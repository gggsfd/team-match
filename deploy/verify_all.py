#!/usr/bin/env python3
"""全面验证TeamMatch服务器部署状态"""
import paramiko
import json

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def run(client, cmd):
    stdin, stdout, stderr = client.exec_command(
        f"bash -s << 'RUN_EOF'\n{cmd}\nRUN_EOF", timeout=60
    )
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    # Filter noise
    noise = ['WARNING', 'debconf', 'dpkg-preconfigure', 'Preparing', 'Unpacking',
             'Setting up', 'Processing triggers', 'Selecting previously']
    if err:
        for line in err.split('\n')[:5]:
            if line.strip() and not any(w in line for w in noise):
                print(f'  [stderr] {line[:200]}')
    return out

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)
    print('[OK] SSH connected')

    # 1. Services
    print('\n' + '=' * 60)
    print('1. Service Status')
    print('=' * 60)
    out = run(client, '''
for svc in nginx mysql php8.4-fpm sshd; do
    status=$(systemctl is-active $svc 2>/dev/null || echo inactive)
    echo "$svc: $status"
done
''')
    print(out)

    # 2. Ports
    print('\n' + '=' * 60)
    print('2. Listening Ports')
    print('=' * 60)
    out = run(client, 'ss -tlnp | grep -E ":(22|80|3306) "')
    print(out)

    # 3. Firewall
    print('\n' + '=' * 60)
    print('3. Firewall (UFW)')
    print('=' * 60)
    out = run(client, 'ufw status')
    print(out)

    # 4. Nginx config
    print('\n' + '=' * 60)
    print('4. Nginx Config')
    print('=' * 60)
    out = run(client, 'cat /etc/nginx/sites-available/teammatch')
    print(out)

    # 5. API tests
    print('\n' + '=' * 60)
    print('5. API Tests')
    print('=' * 60)

    tests = [
        ('GET /api/courses', 'curl -s http://localhost/api/courses'),
        ('GET /api/projects', 'curl -s http://localhost/api/projects'),
        ('GET /api/recommendations', 'curl -s http://localhost/api/recommendations'),
        ('GET /api/projects/1', 'curl -s http://localhost/api/projects/1'),
        ('POST /api/user/login', '''curl -s -X POST http://localhost/api/user/login -H "Content-Type: application/json" -d '{"username":"admin001","password":"123456"}' '''),
        ('GET /api/user/profile', '''curl -s http://localhost/api/user/profile?uid=1'''),
        ('GET /api/admin/users', 'curl -s http://localhost/api/admin/users'),
        ('GET / (frontend)', 'curl -s -o /dev/null -w "HTTP %{http_code} Size:%{size_download}B" http://localhost/'),
    ]

    all_pass = True
    for name, cmd in tests:
        out = run(client, cmd)
        # Try to parse as JSON for pretty display
        try:
            parsed = json.loads(out)
            display = json.dumps(parsed, ensure_ascii=False, indent=2)[:400]
        except:
            display = out[:300] if out else '(empty)'
        print(f'\n  [{name}]')
        for line in display.split('\n'):
            print(f'    {line}')
        # Check for errors
        if '"code":404' in out or '404 Not Found' in out or '接口不存在' in out:
            all_pass = False
            print(f'    >>> FAIL: 404 returned')

    # 6. Database
    print('\n' + '=' * 60)
    print('6. Database Tables')
    print('=' * 60)
    out = run(client, 'mysql -u root team_match -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA=\'team_match\' ORDER BY TABLE_NAME;"')
    print(out)

    # 7. External access
    print('\n' + '=' * 60)
    print('7. External HTTP Access')
    print('=' * 60)
    out = run(client, 'curl -s -o /dev/null -w "HTTP %{http_code}" http://8.138.252.49/')
    print(f'  Frontend external: {out}')
    out = run(client, 'curl -s http://8.138.252.49/api/courses | head -300')
    print(f'  API external courses: {out[:300]}')

    # 8. File structure
    print('\n' + '=' * 60)
    print('8. File Structure')
    print('=' * 60)
    out = run(client, 'ls -la /opt/teammatch/ && echo "---backend---" && ls -la /opt/teammatch/backend/')
    print(out)

    # 9. PHP version & modules
    print('\n' + '=' * 60)
    print('9. PHP Info')
    print('=' * 60)
    out = run(client, 'php -v 2>&1 | head -1 && php -m 2>/dev/null | grep -iE "pdo|mysql|json|mbstring"')
    print(out)

    # 10. Nginx error log (last 5)
    print('\n' + '=' * 60)
    print('10. Nginx Error Log (last 5)')
    print('=' * 60)
    out = run(client, 'tail -5 /var/log/nginx/error.log 2>/dev/null || echo "no error log"')
    print(out)

    client.close()
    print('\n' + '=' * 60)
    print('[DONE] Verification Complete')
    print('=' * 60)

if __name__ == '__main__':
    main()
