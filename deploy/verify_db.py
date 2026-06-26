#!/usr/bin/env python3
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

    # DB tables
    print('=== Database Tables ===')
    out, err = run(client, "mysql -u root -p'Root@Tm#2024#Admin' team_match -e \"SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match' ORDER BY TABLE_NAME;\"")
    if 'ERROR' in out or 'ERROR' in err:
        print(f'DB Error: out={out[:200]}, err={err[:200]}')
    else:
        print(out or '(no output)')

    # User accounts
    print('\n=== User Accounts ===')
    out, err = run(client, "mysql -u root -p'Root@Tm#2024#Admin' team_match -e \"SELECT uid, username, nickname, role FROM user;\" 2>&1")
    if 'ERROR' in out or 'ERROR' in err:
        print(f'Error: {out[:200]} {err[:200]}')
    else:
        print(out or '(no output)')

    # Login test
    print('\n=== Login Test ===')
    out, err = run(client, "curl -s -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"admin001\",\"password\":\"123456\"}'")
    print(out[:500] if out else '(empty)')
    if err:
        print(f'stderr: {err[:200]}')

    # SSH config check
    print('\n=== SSH Security ===')
    out, err = run(client, "grep -E '^(PermitRootLogin|PasswordAuthentication|MaxAuthTries|PubkeyAuthentication)' /etc/ssh/sshd_config")
    print(out)

    # PHP security
    print('\n=== PHP Security ===')
    out, err = run(client, "php -r \"echo 'expose_php='.ini_get('expose_php').' display_errors='.ini_get('display_errors').' log_errors='.ini_get('log_errors');\"")
    print(out)

    client.close()

if __name__ == '__main__':
    main()
