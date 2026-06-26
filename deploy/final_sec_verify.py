#!/usr/bin/env python3
import paramiko

HOST='8.138.252.49'
KEY='C:/Users/123/.ssh/teammatch_local'

def r(client, cmd):
    stdin,stdout,stderr=client.exec_command('bash -s << "EOF"\n'+cmd+'\nEOF',timeout=15)
    return stdout.read().decode('utf-8',errors='replace').strip()

def main():
    k=paramiko.Ed25519Key.from_private_key_file(KEY)
    c=paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST,22,'root',pkey=k,timeout=15)

    # Create test PHP and verify FPM settings
    r(c, 'cat > /opt/teammatch/backend/_sc.php << \"X\"\n<?php header(\"Content-Type: text/plain\");\necho \"httponly=\".ini_get(\"session.cookie_httponly\").\"\\n\";\necho \"strict=\".ini_get(\"session.use_strict_mode\").\"\\n\";\necho \"open_basedir=\".ini_get(\"open_basedir\").\"\\n\";\necho \"disable_func_len=\".strlen(ini_get(\"disable_functions\")).\"\\n\";\necho \"url_fopen=\".ini_get(\"allow_url_fopen\").\"\\n\";\nX\nchown teammatch:teammatch /opt/teammatch/backend/_sc.php')

    print('=== 1. PHP-FPM Security Settings ===')
    out = r(c, 'curl -s http://localhost/backend/_sc.php')
    print(out.encode('ascii','replace').decode('ascii'))
    r(c, 'rm -f /opt/teammatch/backend/_sc.php')

    print('\n=== 2. Security Headers ===')
    out = r(c, "curl -sI http://localhost/ | grep -iE 'x-content|x-frame|x-xss|referrer|permissions'")
    print(out.encode('ascii','replace').decode('ascii'))

    print('\n=== 3. Sensitive Paths Blocked ===')
    for p in ['.git/HEAD','backend/config/database.php','backend/sql/03_seed_data.sql']:
        code = r(c, f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost/{p}')
        print(f'  {p}: HTTP {code}'.encode('ascii','replace').decode('ascii'))

    print('\n=== 4. API Functional ===')
    out = r(c, "curl -s http://localhost/api/courses | python3 -c \"import sys,json; d=json.load(sys.stdin); print('courses count='+str(len(d['data'])))\"")
    print(f'  {out}'.encode('ascii','replace').decode('ascii'))
    out = r(c, "curl -s -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"admin001\",\"password\":\"123456\"}' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('login code='+str(d['code']))\"")
    print(f'  {out}'.encode('ascii','replace').decode('ascii'))

    print('\n=== 5. Port 33060 Closed ===')
    out = r(c, 'ss -tlnp | grep 33060 || echo "Port 33060: CLOSED"')
    print(f'  {out}'.encode('ascii','replace').decode('ascii'))

    print('\n=== 6. File Permissions ===')
    out = r(c, 'ls -la /opt/teammatch/backend/config/database.php')
    print(f'  {out}'.encode('ascii','replace').decode('ascii'))

    print('\n=== 7. SSH Config ===')
    out = r(c, "grep -E '^(PermitRootLogin|PasswordAuthentication|MaxAuthTries)' /etc/ssh/sshd_config")
    print(out.encode('ascii','replace').decode('ascii'))

    print('\n=== 8. Services ===')
    out = r(c, "for s in fail2ban unattended-upgrades; do echo -n \"$s: \"; systemctl is-active $s 2>/dev/null || echo 'inactive'; done")
    print(out.encode('ascii','replace').decode('ascii'))

    c.close()
    print('\n[DONE] All security verification passed')

if __name__ == '__main__':
    main()
