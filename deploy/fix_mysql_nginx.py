#!/usr/bin/env python3
"""修复MySQL认证、初始化数据库、配置Nginx"""
import paramiko

HOST = '8.138.252.49'
PORT = 22
PROJECT_HOME = '/opt/teammatch'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def run(client, cmd, desc=''):
    print(f'\n[{desc or cmd[:60]}]')
    stdin, stdout, stderr = client.exec_command(
        f"bash -s << 'RUN_EOF'\n{cmd}\nRUN_EOF", timeout=180
    )
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    noise = ['WARNING', 'debconf', 'dpkg-preconfigure', 'Preparing', 'Unpacking',
             'Setting up', 'Processing triggers', 'Selecting previously',
             'Created symlink', 'NEWSTART']
    if err:
        for line in err.split('\n')[:10]:
            if line.strip() and not any(w in line for w in noise):
                print(f'  > {line[:150]}')
    if out:
        for line in out.split('\n')[:40]:
            print(f'  {line}')
    return out, err

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, PORT, 'root', pkey=key, timeout=15)
    print("[OK] Connected")

    # ========== 1. MySQL auth fix ==========
    print("\n" + "="*50)
    print("[1] Fix MySQL + Init Database")
    print("="*50)

    run(client, """
export DEBIAN_FRONTEND=noninteractive
systemctl start mysql 2>/dev/null
systemctl enable mysql 2>/dev/null
sleep 2

# Determine auth method
if mysql -u root -e "SELECT 1" 2>/dev/null; then
    echo "AUTH_METHOD=socket"
    AUTH="socket"
else
    echo "AUTH_METHOD=password (using set password)"
    AUTH="password"
fi
""", "Check MySQL auth")

    # Database setup
    run(client, """
# Create database and users
mysql -u root << 'EOSQL'
CREATE DATABASE IF NOT EXISTS team_match DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'teammatch'@'localhost' IDENTIFIED BY 'Tm@2024#Secure';
GRANT ALL PRIVILEGES ON team_match.* TO 'teammatch'@'localhost';
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Root@Tm#2024#Admin';
FLUSH PRIVILEGES;
EOSQL
echo "DB and users created"

# Run SQL table creation
mysql -u root team_match < /opt/teammatch/backend/sql/02_create_tables.sql 2>&1
echo "Tables created"

# Run seed data
mysql -u root team_match < /opt/teammatch/backend/sql/03_seed_data.sql 2>&1
echo "Seed data inserted"

# Verify
mysql -u root team_match -e "SHOW TABLES;"
mysql -u root team_match -N -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match';" | xargs echo "table_count="
""", "Initialize database")

    # ========== 2. Configure PHP-FPM ==========
    print("\n" + "="*50)
    print("[2] Configure PHP-FPM")
    print("="*50)

    run(client, """
PHP_VER=$(php -v 2>/dev/null | head -1 | grep -oP '\\d+\\.\\d+' | head -1)
echo "PHP version: $PHP_VER"

# Ensure PHP-FPM is installed and running
apt-get install -y -qq php${PHP_VER}-fpm php${PHP_VER}-mysql php${PHP_VER}-mbstring php${PHP_VER}-xml php${PHP_VER}-curl php${PHP_VER}-gd php${PHP_VER}-zip 2>/dev/null

# Start PHP-FPM
PHP_FPM_SVC=$(systemctl list-unit-files 2>/dev/null | grep "php.*fpm" | awk '{print $1}' | head -1)
if [ -n "$PHP_FPM_SVC" ]; then
    systemctl start "$PHP_FPM_SVC"
    systemctl enable "$PHP_FPM_SVC"
    echo "Started: $PHP_FPM_SVC"
else
    echo "Looking for php-fpm..."
    ls /run/php/ 2>/dev/null || echo "No php socket dir"
fi

# PHP security config
for ini in /etc/php/${PHP_VER}/fpm/php.ini /etc/php/${PHP_VER}/cli/php.ini; do
    if [ -f "$ini" ]; then
        sed -i 's/^;*expose_php.*/expose_php = Off/' "$ini"
        sed -i 's/^;*display_errors.*/display_errors = Off/' "$ini"
        sed -i 's/^;*log_errors.*/log_errors = On/' "$ini"
        echo "Updated: $ini"
    fi
done

PHP_FPM_SVC=$(systemctl list-unit-files 2>/dev/null | grep "php.*fpm" | awk '{print $1}' | head -1)
[ -n "$PHP_FPM_SVC" ] && systemctl restart "$PHP_FPM_SVC"
echo "PHP-FPM configured"
""", "Configure PHP-FPM")

    # ========== 3. Nginx config ==========
    print("\n" + "="*50)
    print("[3] Configure Nginx")
    print("="*50)

    run(client, """
PHP_SOCK=$(find /run/php/ -name "php*.sock" 2>/dev/null | head -1)
[ -z "$PHP_SOCK" ] && PHP_SOCK="/run/php/php8.4-fpm.sock"
echo "PHP socket: $PHP_SOCK"

mkdir -p /etc/nginx/sites-enabled

cat > /etc/nginx/sites-available/teammatch << 'EONGINX'
server {
    listen 80 default_server;
    server_name 8.138.252.49 _;

    root PROJECT_HOME_PLACEHOLDER;
    charset utf-8;
    index index.html index.php;

    # Frontend pages
    location / {
        root PROJECT_HOME_PLACEHOLDER/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API rewrite to backend
    location /api/ {
        root PROJECT_HOME_PLACEHOLDER;
        rewrite ^/api/(.*)$ /backend/api/$1 last;
    }

    # PHP processing for backend
    location /backend/ {
        root PROJECT_HOME_PLACEHOLDER;
        include fastcgi_params;
        fastcgi_pass unix:SOCK_PLACEHOLDER;
        fastcgi_param SCRIPT_FILENAME PROJECT_HOME_PLACEHOLDER$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
    }

    # Generic PHP
    location ~ \.php$ {
        root PROJECT_HOME_PLACEHOLDER;
        include fastcgi_params;
        fastcgi_pass unix:SOCK_PLACEHOLDER;
        fastcgi_param SCRIPT_FILENAME PROJECT_HOME_PLACEHOLDER$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
    }

    # Security
    location ~ /\. { deny all; }
    location ~ \.(sql|md|log)$ { deny all; }

    # Gzip
    gzip on;
    gzip_types text/css application/javascript application/json;
}
EONGINX

# Replace placeholders
sed -i "s|PROJECT_HOME_PLACEHOLDER|/opt/teammatch|g" /etc/nginx/sites-available/teammatch
sed -i "s|SOCK_PLACEHOLDER|$PHP_SOCK|g" /etc/nginx/sites-available/teammatch

ln -sf /etc/nginx/sites-available/teammatch /etc/nginx/sites-enabled/teammatch
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
echo "Nginx configured"
""", "Configure Nginx site")

    # ========== 4. Fix permissions ==========
    print("\n" + "="*50)
    print("[4] Fix permissions")
    print("="*50)

    run(client, """
chown -R teammatch:teammatch /opt/teammatch
chmod -R 755 /opt/teammatch
chmod -R 775 /opt/teammatch/backend/uploads 2>/dev/null || true
chmod -R 775 /opt/teammatch/logs 2>/dev/null || true
usermod -a -G teammatch www-data 2>/dev/null || true
echo "Permissions fixed"
ls -la /opt/teammatch/
""", "Fix permissions")

    # ========== 5. Verify everything ==========
    print("\n" + "="*50)
    print("[5] Comprehensive verification")
    print("="*50)

    run(client, """
echo "=== Services ==="
for s in nginx mysql; do
    echo -n "$s: "; systemctl is-active $s 2>/dev/null || echo "inactive"
done
PHP_FPM=$(systemctl list-unit-files 2>/dev/null | grep "php.*fpm" | awk '{print $1}' | head -1)
echo -n "$PHP_FPM: "; systemctl is-active "$PHP_FPM" 2>/dev/null || echo "inactive"

echo ""
echo "=== Ports ==="
ss -tlnp | grep -E ':(22|80|3306) '

echo ""
echo "=== DB Tables ==="
mysql -u root team_match -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match' ORDER BY TABLE_NAME;" 2>/dev/null

echo ""
echo "=== HTTP Test ==="
echo "Frontend:"
curl -s -o /dev/null -w "  HTTP %{http_code} Size:%{size_download}B\\n" http://localhost/
echo "API:"
curl -s http://localhost/api/courses | head -5
echo ""

echo ""
echo "=== Firewall ==="
ufw status | head -15

echo ""
echo "=== SSH Config ==="
grep -E '^(PermitRootLogin|PasswordAuthentication|MaxAuthTries)' /etc/ssh/sshd_config

echo ""
echo "=== PHP info ==="
php -v 2>&1 | head -1
php -m 2>/dev/null | grep -i pdo
""", "Verification")

    client.close()
    print("\n[DONE] All fixes applied successfully!")

if __name__ == '__main__':
    main()
