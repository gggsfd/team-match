#!/usr/bin/env python3
"""通过SSH修复 admin/users.php 的PDO链式调用bug"""
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

    # Fix: replace the chained prepare()->execute()->fetch() on line 34
    # The fix breaks the chain into 3 separate lines
    print('=== Fixing line 34 ===')
    out, err = run(client, """
cd /opt/teammatch/backend/api/admin

# Line 34 has: $total = (int)$db->prepare(...)->execute($params)->fetch()['cnt'];
# We need to replace it with 3 lines

# Use python3 for reliable text replacement
python3 << 'PYFIX'
import re

with open('users.php', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the chained call
old = '$total = (int)$db->prepare("SELECT COUNT(*) AS cnt FROM user u WHERE {$wsql}")->execute($params)->fetch()[\'cnt\'];'
new = '''$countStmt = $db->prepare("SELECT COUNT(*) AS cnt FROM user u WHERE {$wsql}");
    $countStmt->execute($params);
    $total = (int)$countStmt->fetch()['cnt'];'''

if old in content:
    content = content.replace(old, new)
    with open('users.php', 'w', encoding='utf-8') as f:
        f.write(content)
    print('FIXED: line 34 replaced')
else:
    print('NOT FOUND: line 34 pattern not matched')
    # Show what's on line 34
    lines = content.split('\\n')
    for i, line in enumerate(lines[32:40], start=33):
        print(f'  {i}: {line[:120]}')
PYFIX
""")
    print(out)
    if err:
        print(f'ERR: {err[:300]}')

    # Also fix the POST section (lines 67-69) and PUT section (line 98)
    # These also have prepare()->execute() chaining which works but is inconsistent
    print('\n=== Verify fix ===')
    out, err = run(client, "sed -n '33,38p' /opt/teammatch/backend/api/admin/users.php")
    print(out)

    # Test admin API
    print('\n=== Test admin users API ===')
    out, err = run(client, """
curl -s -c /tmp/test_cookies.txt -X POST http://localhost/api/user/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin001","password":"123456"}' > /dev/null
curl -s -b /tmp/test_cookies.txt 'http://localhost/api/admin/users' 2>&1 | head -500
""")
    print(out[:600] if out else '(empty)')

    # External API test
    print('\n=== External courses API ===')
    out, err = run(client, "curl -s 'http://8.138.252.49/api/courses' 2>&1 | head -200")
    print(out[:400] if out else '(empty)')

    client.close()
    print('\n[DONE]')

if __name__ == '__main__':
    main()
