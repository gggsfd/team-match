#!/usr/bin/env python3
import paramiko

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def do_fix():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)

    # Read the fix script
    with open('deploy/fix_admin_line34.sh', 'r') as f:
        script = f.read()

    # Run it via bash
    stdin, stdout, stderr = client.exec_command(
        "bash -s << 'SCRIPT_EOF'\n" + script + "\nSCRIPT_EOF",
        timeout=30
    )
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print('STDERR:', err[:300])

    # Test the API
    print('\n--- Testing admin API ---')
    stdin, stdout, stderr = client.exec_command(
        "curl -s -c /tmp/tc3.txt -X POST http://localhost/api/user/login "
        "-H 'Content-Type: application/json' "
        "-d '{\"username\":\"admin001\",\"password\":\"123456\"}' > /dev/null; "
        "curl -s -b /tmp/tc3.txt http://localhost/api/admin/users | head -400",
        timeout=30
    )
    out = stdout.read().decode('utf-8', errors='replace')
    print(out[:600])

    client.close()

if __name__ == '__main__':
    do_fix()
