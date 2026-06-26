#!/usr/bin/env python3
"""部署更新：上传新代码 + 重新初始化数据库"""
import paramiko
import os

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'
LOCAL_ROOT = 'd:/Mycode/data_sysytem'

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)

    sftp = client.open_sftp()

    # Files to upload
    files = [
        'backend/index.php',
        'backend/sql/03_seed_data.sql',
        'backend/api/admin/users.php',
        'backend/api/admin/stats.php',
        'backend/api/admin/projects.php',
    ]

    for f in files:
        local_path = os.path.join(LOCAL_ROOT, f)
        remote_path = f'/opt/teammatch/{f}'
        # Ensure directory exists
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)

        sftp.put(local_path, remote_path)
        print(f'[UPLOAD] {f}')

    sftp.close()

    # Fix permissions
    stdin, stdout, stderr = client.exec_command(
        'chown -R teammatch:teammatch /opt/teammatch/backend && '
        'chmod -R 755 /opt/teammatch/backend',
        timeout=10
    )
    print('[OK] Permissions set')

    # Re-initialize database (drop & recreate data)
    print('\n=== Re-initializing Database ===')
    cmd = """bash -s << 'DBEOF'
mysql -u root -p'Root@Tm#2024#Admin' team_match << 'EOSQL'
-- Disable foreign key checks temporarily
SET FOREIGN_KEY_CHECKS = 0;
-- Truncate all tables in correct order
TRUNCATE TABLE progress;
TRUNCATE TABLE application;
TRUNCATE TABLE member;
TRUNCATE TABLE project_skill;
TRUNCATE TABLE project;
TRUNCATE TABLE user_skill;
TRUNCATE TABLE user;
TRUNCATE TABLE skill;
TRUNCATE TABLE course;
-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;
EOSQL

# Re-run seed data
mysql -u root -p'Root@Tm#2024#Admin' team_match < /opt/teammatch/backend/sql/03_seed_data.sql 2>&1
echo "Seed data re-loaded"

# Verify counts
mysql -u root -p'Root@Tm#2024#Admin' team_match -e "
SELECT 'course' AS tbl, COUNT(*) AS cnt FROM course
UNION ALL SELECT 'user', COUNT(*) FROM user
UNION ALL SELECT 'skill', COUNT(*) FROM skill
UNION ALL SELECT 'project', COUNT(*) FROM project
UNION ALL SELECT 'user_skill', COUNT(*) FROM user_skill
UNION ALL SELECT 'project_skill', COUNT(*) FROM project_skill
UNION ALL SELECT 'member', COUNT(*) FROM member
UNION ALL SELECT 'application', COUNT(*) FROM application
UNION ALL SELECT 'progress', COUNT(*) FROM progress;
"
DBEOF"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        # Filter noise
        for line in err.split('\n'):
            if line.strip() and 'Warning' not in line:
                print(f'  ERR: {line[:200]}')

    # Test APIs
    print('\n=== API Tests ===')
    tests = [
        ('GET /api/courses', 'curl -s http://localhost/api/courses | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\'courses: {len(d[\\\"data\\\"])}\')"'),
        ('GET /api/projects', 'curl -s http://localhost/api/projects | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\'projects: total={d[\\\"data\\\"][\\\"total\\\"]}\')"'),
        ('Login admin', 'curl -s -c /tmp/adm_cookies.txt -X POST http://localhost/api/user/login -H "Content-Type: application/json" -d \'{"username":"admin001","password":"123456"}\' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\'login: {d[\\\"code\\\"]}\')"'),
        ('GET /api/admin/stats', 'curl -s -b /tmp/adm_cookies.txt http://localhost/api/admin/stats | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d[\\\"data\\\"], indent=2))"'),
        ('GET /api/admin/projects', 'curl -s -b /tmp/adm_cookies.txt http://localhost/api/admin/projects | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\'admin projects: total={d[\\\"data\\\"][\\\"total\\\"]}\')"'),
        ('GET /api/admin/users', 'curl -s -b /tmp/adm_cookies.txt http://localhost/api/admin/users | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\'admin users: total={d[\\\"data\\\"][\\\"total\\\"]}\')"'),
    ]
    for name, cmd in tests:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        print(f'  [{name}] {out}')

    client.close()
    print('\n[DONE] Deployment complete')

if __name__ == '__main__':
    main()
