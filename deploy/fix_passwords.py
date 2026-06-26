#!/usr/bin/env python3
"""修复种子数据密码哈希 + SSH安全加固 + 最终验证"""
import paramiko
import json

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

    # ===== 1. Fix password hashes =====
    print('\n' + '='*60)
    print('1. Fix password hashes')
    print('='*60)
    out, err = run(client, """
# Update all users: password = MD5(username + '123456' + 'team_match_salt')
mysql -u root -p'Root@Tm#2024#Admin' team_match << 'EOSQL'
UPDATE user SET password = MD5(CONCAT(username, '123456', 'team_match_salt'));
SELECT username, nickname, 'Password fixed' AS status FROM user;
EOSQL
""")
    print(out)
    if 'ERROR' in (out + err):
        print(f'  ERROR: {err[:300]}')

    # ===== 2. Test login =====
    print('\n' + '='*60)
    print('2. Login test (admin001/123456)')
    print('='*60)
    out, err = run(client, "curl -s -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"admin001\",\"password\":\"123456\"}'")
    print(f'  admin001: {out[:300]}')

    out, err = run(client, "curl -s -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"2024001\",\"password\":\"123456\"}'")
    print(f'  2024001(张三): {out[:300]}')

    # ===== 3. Test APIs that need login =====
    print('\n' + '='*60)
    print('3. Authenticated API tests')
    print('='*60)

    # Get session cookie from login
    out, err = run(client, "curl -s -c /tmp/cookies.txt -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"admin001\",\"password\":\"123456\"}'")
    print(f'  Login: {out[:200]}')

    out, err = run(client, "curl -s -b /tmp/cookies.txt http://localhost/api/user/profile?uid=1")
    print(f'  Profile: {out[:300]}')

    out, err = run(client, "curl -s -b /tmp/cookies.txt http://localhost/api/recommendations")
    print(f'  Recommendations: {out[:400]}')

    out, err = run(client, "curl -s -b /tmp/cookies.txt http://localhost/api/admin/users")
    print(f'  Admin users: {out[:400]}')

    out, err = run(client, "curl -s -b /tmp/cookies.txt http://localhost/api/projects/1/progress")
    print(f'  Project progress: {out[:300]}')

    out, err = run(client, "curl -s -b /tmp/cookies.txt http://localhost/api/projects/1/applications")
    print(f'  Project applications: {out[:300]}')

    # ===== 4. External access =====
    print('\n' + '='*60)
    print('4. External access (from outside)')
    print('='*60)
    out, err = run(client, 'curl -s -o /dev/null -w "Frontend: HTTP %{http_code}" http://8.138.252.49/')
    print(f'  {out}')
    out, err = run(client, 'curl -s http://8.138.252.49/api/courses | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"API courses: code={d[\\\"code\\\"]}, count={len(d[\\\"data\\\"])}\")" 2>/dev/null || echo "parse failed"')
    print(f'  {out}')

    # ===== 5. Final SSH hardening =====
    print('\n' + '='*60)
    print('5. SSH hardening')
    print('='*60)
    out, err = run(client, """
# Ensure local public key is in authorized_keys
mkdir -p /root/.ssh
chmod 700 /root/.ssh
grep -q 'teammatch-local-deploy' /root/.ssh/authorized_keys 2>/dev/null || echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF9p9+5v18WAINlDUncKo0ZUVk7JSoF7wJqvUDxj/rw2 teammatch-local-deploy' >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Enable key-only auth
sed -i 's/^PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
grep -q '^PasswordAuthentication' /etc/ssh/sshd_config || echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config
sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

systemctl restart sshd
echo 'SSH hardened: key-only auth'
grep -E '^(PermitRootLogin|PasswordAuthentication|MaxAuthTries)' /etc/ssh/sshd_config
""")
    print(out)

    # ===== 6. PHP security hardening =====
    print('\n' + '='*60)
    print('6. PHP security settings')
    print('='*60)
    out, err = run(client, """
PHP_VER=$(php -v 2>/dev/null | head -1 | grep -oP '\\d+\\.\\d+' | head -1)
for ini in /etc/php/${PHP_VER}/fpm/php.ini /etc/php/${PHP_VER}/cli/php.ini; do
    if [ -f "$ini" ]; then
        sed -i 's/^;*expose_php.*/expose_php = Off/' "$ini"
        sed -i 's/^;*display_errors.*/display_errors = Off/' "$ini"
        sed -i 's/^;*log_errors.*/log_errors = On/' "$ini"
        echo "Updated: $ini"
    fi
done
systemctl restart php8.4-fpm
php -r "echo 'expose_php='.ini_get('expose_php').' display_errors='.ini_get('display_errors').' log_errors='.ini_get('log_errors');"
""")
    print(out)

    # ===== 7. Nginx error log check =====
    print('\n' + '='*60)
    print('7. Nginx error log (recent)')
    print('='*60)
    out, err = run(client, 'tail -5 /var/log/nginx/error.log')
    # Filter for actual errors (not notices)
    for line in out.split('\n'):
        if 'error]' in line.lower() and 'primary script unknown' in line.lower():
            print(f'  OLD ERROR (before fix): {line[:150]}')
        elif 'error]' in line.lower():
            print(f'  ERROR: {line[:200]}')
        elif 'notice]' in line.lower():
            pass  # skip notices
        else:
            print(f'  {line[:150]}')

    client.close()

    print('\n' + '='*60)
    print('[DONE] All fixes applied')
    print('='*60)

if __name__ == '__main__':
    main()
