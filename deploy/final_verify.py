#!/usr/bin/env python3
"""最终全面验证 - 生成部署报告"""
import paramiko

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def run(client, cmd):
    stdin, stdout, stderr = client.exec_command(
        "bash -s << 'RUN_EOF'\n" + cmd + "\nRUN_EOF", timeout=30
    )
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)

    results = {}

    # 1. Services
    out, _ = run(client, '''
for svc in nginx mysql php8.4-fpm sshd; do
    echo "$svc: $(systemctl is-active $svc 2>/dev/null || echo inactive)"
done
''')
    results['services'] = out

    # 2. Ports
    out, _ = run(client, 'ss -tlnp | grep -E ":(22|80|3306) "')
    results['ports'] = out

    # 3. Firewall
    out, _ = run(client, 'ufw status | head -15')
    results['firewall'] = out

    # 4. SSH security
    out, _ = run(client, 'grep -E "^(PermitRootLogin|PasswordAuthentication|MaxAuthTries|PubkeyAuthentication)" /etc/ssh/sshd_config')
    results['ssh'] = out

    # 5. PHP security
    out, _ = run(client, 'php -r "echo \"PHP=\" . phpversion() . \" expose=\" . ini_get(\"expose_php\") . \" disp_err=\" . ini_get(\"display_errors\") . \" log_err=\" . ini_get(\"log_errors\");"')
    results['php'] = out

    # 6. DB tables
    out, _ = run(client, "mysql -u root -p'Root@Tm#2024#Admin' team_match -e \"SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match' ORDER BY TABLE_NAME;\"")
    results['db'] = out

    # 7. API tests
    api_results = []
    # Login and store cookie
    run(client, "curl -s -c /tmp/final_cookies.txt -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"admin001\",\"password\":\"123456\"}' > /dev/null")

    tests = [
        ('GET /api/courses', 'curl -s http://localhost/api/courses'),
        ('GET /api/projects', 'curl -s http://localhost/api/projects'),
        ('GET /api/projects/1', 'curl -s http://localhost/api/projects/1'),
        ('GET /api/user/profile?uid=1', 'curl -s -b /tmp/final_cookies.txt "http://localhost/api/user/profile?uid=1"'),
        ('GET /api/recommendations', 'curl -s -b /tmp/final_cookies.txt http://localhost/api/recommendations'),
        ('GET /api/admin/users', 'curl -s -b /tmp/final_cookies.txt http://localhost/api/admin/users'),
        ('GET /api/projects/1/progress', 'curl -s -b /tmp/final_cookies.txt http://localhost/api/projects/1/progress'),
        ('POST /api/user/login', "curl -s -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"admin001\",\"password\":\"123456\"}'"),
    ]
    for name, cmd in tests:
        out, _ = run(client, cmd)
        status = '200' if '"code":200' in out else 'FAIL'
        if '"code":401' in out:
            status = '401(need auth)'
        elif '"code":400' in out:
            status = '400'
        api_results.append(f'  [{status}] {name}')

    results['api'] = '\n'.join(api_results)

    # 8. Frontend
    out, _ = run(client, 'curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost/')
    results['frontend_local'] = out
    out, _ = run(client, 'curl -s -o /dev/null -w "HTTP %{http_code}" http://8.138.252.49/')
    results['frontend_ext'] = out

    # 9. Nginx errors
    out, _ = run(client, "grep 'error]' /var/log/nginx/error.log | tail -3")
    results['nginx_errors'] = out

    # Print report
    print('=' * 60)
    print('  TeamMatch Server Deployment Final Report')
    print('=' * 60)

    print('\n1. Services:')
    for line in results.get('services', '').split('\n'):
        print(f'   {line}')

    print('\n2. Ports:')
    for line in results.get('ports', '').split('\n'):
        print(f'   {line}')

    print('\n3. Firewall:')
    for line in results.get('firewall', '').split('\n')[:10]:
        print(f'   {line}')

    print('\n4. SSH Security:')
    for line in results.get('ssh', '').split('\n'):
        print(f'   {line}')

    print('\n5. PHP:')
    print(f'   {results.get("php", "")}')

    print('\n6. Database (9 tables):')
    for line in results.get('db', '').split('\n'):
        print(f'   {line}')

    print('\n7. API Tests:')
    for line in results.get('api', '').split('\n'):
        print(line)

    print('\n8. Frontend:')
    print(f'   Local: {results.get("frontend_local", "")}')
    print(f'   External: {results.get("frontend_ext", "")}')

    print('\n9. Nginx Errors (recent):')
    for line in results.get('nginx_errors', '').split('\n'):
        if line.strip():
            print(f'   {line[:200]}')

    print('\n' + '=' * 60)
    print('  Report Complete')
    print('=' * 60)

    client.close()

if __name__ == '__main__':
    main()
