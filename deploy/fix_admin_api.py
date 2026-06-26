#!/usr/bin/env python3
"""修复 admin/users.php 的PDO链式调用bug"""
import paramiko

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def run(client, cmd):
    stdin, stdout, stderr = client.exec_command(
        f"bash -s << 'RUN_EOF'\n{cmd}\nRUN_EOF", timeout=30
    )
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)
    print('[OK] SSH connected')

    # Show current line 34
    print('\n=== Current line 34 ===')
    out, err = run(client, "sed -n '32,36p' /opt/teammatch/backend/api/admin/users.php")
    print(out)

    # Fix the method chaining bug
    print('\n=== Fixing admin/users.php ===')
    out, err = run(client, """
cd /opt/teammatch/backend/api/admin

# Use sed to fix the chaining pattern on line 34
# Break the chain: prepare()->execute()->fetch()
sed -i '34s/.*/    $countStmt = $db->prepare("SELECT COUNT(*) AS cnt FROM user u WHERE {$wsql}");/' users.php
sed -i '35i\\    $countStmt->execute($params);' users.php
sed -i '36s/.*/    $total = (int)$countStmt->fetch()['"'"'cnt'"'"'];/' users.php

# Show the fixed lines
sed -n '32,40p' users.php
""")
    print(out)

    # Test admin API again
    print('\n=== Test admin users API ===')
    out, err = run(client, """
# Login and get cookie
curl -s -c /tmp/cookies2.txt -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{"username":"admin001","password":"123456"}' > /dev/null
# Test admin API
curl -s -b /tmp/cookies2.txt http://localhost/api/admin/users | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'code={d[\"code\"]}, total_users={d[\"data\"][\"total\"]}, page_size={d[\"data\"][\"page_size\"]}')" 2>/dev/null || curl -s -b /tmp/cookies2.txt http://localhost/api/admin/users
""")
    print(out)

    # Test external access
    print('\n=== External API test ===')
    out, err = run(client, "curl -s http://8.138.252.49/api/courses | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'code={d[\\\"code\\\"]}, courses_count={len(d[\\\"data\\\"])}')\" 2>/dev/null || echo 'parse failed'")
    print(out)

    # Check Nginx error log
    print('\n=== Nginx recent errors ===')
    out, err = run(client, "grep 'error]' /var/log/nginx/error.log | tail -3")
    for line in out.split('\n'):
        if 'error]' in line:
            print(f'  {line[:200]}')

    client.close()
    print('\n[DONE]')

if __name__ == '__main__':
    main()
