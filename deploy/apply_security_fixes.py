#!/usr/bin/env python3
"""应用安全审计发现的所有修复"""
import paramiko

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def run(client, cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(
        "bash -s << 'RUN_EOF'\n" + cmd + "\nRUN_EOF", timeout=timeout
    )
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    noise = ['WARNING', 'debconf', 'Preparing', 'Unpacking', 'Setting up', 'Processing triggers']
    if err:
        for line in err.split('\n')[:10]:
            if line.strip() and not any(w in line for w in noise):
                print(f'  ERR: {line[:150]}')
    return out

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)

    # ===== 1. Nginx: Add security headers + fix sensitive file protection =====
    print('[1] Nginx security hardening')
    out = run(client, """
cat > /etc/nginx/sites-available/teammatch << 'NGINXEOF'
server {
    listen 80 default_server;
    server_name 8.138.252.49 _;
    charset utf-8;

    root /opt/teammatch;

    # ===== Security Headers =====
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    location / {
        root /opt/teammatch/frontend;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        include fastcgi_params;
        fastcgi_pass unix:/run/php/php8.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME /opt/teammatch/backend/index.php;
        fastcgi_param SCRIPT_NAME /index.php;
    }

    # Deny hidden files
    location ~ /\\. { deny all; access_log off; log_not_found off; }

    # Deny sensitive file types
    location ~ \\.(sql|md|log|sh|py|yml|yaml|json|lock|dist|ini)$ { deny all; access_log off; log_not_found off; }

    # Deny access to specific sensitive paths
    location ~ ^/(backend/config|backend/sql|backend/tests|deploy|\\.git) { deny all; access_log off; log_not_found off; }

    gzip on;
    gzip_types text/css application/javascript application/json text/html;
}
NGINXEOF

nginx -t && systemctl reload nginx && echo "NGINX_OK" || echo "NGINX_FAIL"
""")
    print(out)

    # Verify headers
    print('\n--- Security headers verification ---')
    out = run(client, "curl -sI http://localhost/ | grep -iE 'x-content-type|x-frame|x-xss|referrer-policy|permissions-policy'")
    print(out)

    # ===== 2. PHP security hardening =====
    print('\n[2] PHP security hardening')
    out = run(client, """
PHPVER=$(php -v 2>/dev/null | head -1 | grep -oP '\\d+\\.\\d+' | head -1)
PHPINI="/etc/php/${PHPVER}/fpm/php.ini"

# Backup
cp "$PHPINI" "${PHPINI}.bak"

# Session security
sed -i 's/^;*session.cookie_httponly.*/session.cookie_httponly = 1/' "$PHPINI"
sed -i 's/^;*session.use_strict_mode.*/session.use_strict_mode = 1/' "$PHPINI"
sed -i 's/^;*session.cookie_samesite.*/session.cookie_samesite = "Lax"/' "$PHPINI"

# Disable dangerous functions
DANGEROUS="exec,system,passthru,shell_exec,popen,proc_open,pcntl_exec,putenv,apache_child_terminate,apache_setenv,define_syslog_variables,escapeshellarg,escapeshellcmd,eval,assert,create_function,parse_ini_file,show_source"
sed -i "s/^;*disable_functions.*/disable_functions = ${DANGEROUS}/" "$PHPINI"

# open_basedir
sed -i 's|^;*open_basedir.*|open_basedir = /opt/teammatch/:/tmp/:/usr/share/php/|' "$PHPINI"

# Additional hardening
sed -i 's/^;*allow_url_fopen.*/allow_url_fopen = Off/' "$PHPINI"
sed -i 's/^;*allow_url_include.*/allow_url_include = Off/' "$PHPINI"

# Restart PHP-FPM
systemctl restart php${PHPVER}-fpm
echo "PHP_FPM_RESTARTED"

# Verify
php -r "echo 'httponly='.ini_get('session.cookie_httponly').' |strict='.ini_get('session.use_strict_mode').' |samesite='.ini_get('session.cookie_samesite').' |disable_func='.substr(ini_get('disable_functions'),0,50).'... |open_basedir='.ini_get('open_basedir').' |url_fopen='.ini_get('allow_url_fopen').' |url_include='.ini_get('allow_url_include');"
""")
    print(out)

    # ===== 3. File permissions =====
    print('\n[3] Fix file permissions')
    out = run(client, """
# Database config - restrict
chmod 640 /opt/teammatch/backend/config/database.php
chown teammatch:www-data /opt/teammatch/backend/config/database.php

# SSH keys
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys

# Check results
ls -la /opt/teammatch/backend/config/database.php
ls -la /root/.ssh/
""")
    print(out)

    # ===== 4. System updates =====
    print('\n[4] System updates')
    out = run(client, """
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq 2>&1 | tail -1
apt-get upgrade -y -qq 2>&1 | tail -3
echo "UPDATES_DONE"
""", timeout=120)
    print(out[:500])

    # ===== 5. Disable MySQL X Protocol =====
    print('\n[5] Disable MySQL X Protocol (port 33060)')
    out = run(client, """
if [ -f /etc/mysql/mysql.conf.d/mysqld.cnf ]; then
    CONF=/etc/mysql/mysql.conf.d/mysqld.cnf
else
    CONF=/etc/mysql/my.cnf
fi

# Disable mysqlx
if grep -q 'mysqlx' "$CONF"; then
    sed -i 's/^#*mysqlx.*/mysqlx = OFF/' "$CONF"
else
    echo 'mysqlx = OFF' >> "$CONF"
fi

systemctl restart mysql
sleep 2
ss -tlnp | grep 33060 || echo "PORT_33060_CLOSED"
""")
    print(out)

    # ===== 6. Final verification =====
    print('\n[6] Final verification')

    # Test APIs still work
    out = run(client, "curl -s http://localhost/api/courses | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'API courses: code={d[\\\"code\\\"]}, count={len(d[\\\"data\\\"])}')\"")
    print(f'  {out}')

    out = run(client, "curl -s -X POST http://localhost/api/user/login -H 'Content-Type: application/json' -d '{\"username\":\"admin001\",\"password\":\"123456\"}' | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'Login: code={d[\\\"code\\\"]}')\"")
    print(f'  {out}')

    # Test that sensitive paths are blocked
    out = run(client, 'curl -s -o /dev/null -w "%{http_code}" http://localhost/.git/HEAD')
    print(f'  .git access: HTTP {out} (should be 403/404)')

    out = run(client, 'curl -s -o /dev/null -w "%{http_code}" http://localhost/backend/config/database.php')
    print(f'  database.php access: HTTP {out} (should be 403)')

    out = run(client, 'curl -s -o /dev/null -w "%{http_code}" http://localhost/backend/sql/03_seed_data.sql')
    print(f'  seed_data.sql access: HTTP {out} (should be 403)')

    # Verify 33060 closed
    out = run(client, 'ss -tlnp | grep 33060 || echo "33060_closed"')
    print(f'  Port 33060: {out.strip()}')

    # Verify PHP security settings
    out = run(client, "php -r \"echo 'open_basedir='.ini_get('open_basedir').' |disable_func_len='.strlen(ini_get('disable_functions'));\"")
    print(f'  {out}')

    client.close()
    print('\n[DONE] All security fixes applied')

if __name__ == '__main__':
    main()
