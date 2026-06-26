#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeamMatch 环境修复脚本 - 修复Nginx/MySQL/PHP-FPM安装问题
"""
import paramiko
import sys
import time

HOST = '8.138.252.49'
PORT = 22
USER = 'root'
PASSWORD = 'admin12345789@'
PROJECT_HOME = '/opt/teammatch'

class Fixer:
    def __init__(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        print("[连接] 连接到服务器...")
        self.client.connect(HOST, PORT, USER, PASSWORD, timeout=30)
        print("[OK] 已连接")

    def close(self):
        self.client.close()

    def run(self, cmd, desc=''):
        print(f"\n[执行] {desc or cmd[:80]}")
        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=180)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if err:
            non_warn = [l for l in err.split('\n') if 'WARNING' not in l and 'Warning' not in l and 'debconf' not in l]
            if non_warn:
                print(f"  ERR: {'; '.join(non_warn[:5])}")
        if out:
            for line in out.split('\n')[:25]:
                print(f"  {line}")
        return out, err

    def run_script(self, script, desc=''):
        print(f"\n[脚本] {desc}")
        stdin, stdout, stderr = self.client.exec_command(
            f"bash -s << 'FIX_EOF'\n{script}\nFIX_EOF", timeout=300
        )
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if err:
            lines = [l for l in err.split('\n') if 'WARNING' not in l and 'Warning' not in l and 'debconf' not in l]
            if lines:
                print(f"  ERR: {'; '.join(lines[:5])}")
        if out:
            for line in out.split('\n')[:40]:
                print(f"  {line}")
        return out, err


def main():
    fixer = Fixer()
    try:
        fixer.connect()

        # ========== 1. 停用Apache2，安装Nginx ==========
        print("\n" + "="*50)
        print("[步骤1] 停用Apache2，安装配置Nginx")
        print("="*50)

        fixer.run_script("""
export DEBIAN_FRONTEND=noninteractive

# 停止并禁用Apache2
systemctl stop apache2 2>/dev/null
systemctl disable apache2 2>/dev/null
echo "Apache2已停止"

# 安装Nginx
apt-get install -y -qq nginx 2>&1
echo "Nginx安装完成"

# 确保PHP-FPM已安装
apt-get install -y -qq php8.4-fpm php8.4-mysql php8.4-mbstring php8.4-xml php8.4-curl php8.4-gd php8.4-zip 2>&1
echo "PHP-FPM及相关扩展安装完成"

# 查看PHP-FPM socket路径
PHP_SOCK=$(find /run/php/ -name "php*.sock" 2>/dev/null | head -1)
echo "PHP-FPM socket: $PHP_SOCK"
""", "安装Nginx+PHP-FPM")

        # ========== 2. 获取PHP版本信息 ==========
        out, _ = fixer.run("php -v 2>&1 | head -1", "获取PHP版本")
        php_ver = out.split()[1].split('.')[0:2] if out else ['8','4']
        php_ver_str = f"{php_ver[0]}.{php_ver[1]}"
        print(f"PHP版本: {php_ver_str}")

        # ========== 3. 安装并配置MySQL ==========
        print("\n" + "="*50)
        print("[步骤2] 安装配置MySQL")
        print("="*50)

        fixer.run_script("""
export DEBIAN_FRONTEND=noninteractive

# 安装MySQL
apt-get install -y -qq mysql-server 2>&1
systemctl start mysql 2>/dev/null
systemctl enable mysql 2>/dev/null
echo "MySQL安装完成"

# 初始化
mysql -u root << 'EOSQL'
CREATE DATABASE IF NOT EXISTS team_match DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'teammatch'@'localhost' IDENTIFIED BY 'Tm@2024#Secure';
GRANT ALL PRIVILEGES ON team_match.* TO 'teammatch'@'localhost';
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Root@Tm#2024#Admin';
FLUSH PRIVILEGES;
SELECT 'MySQL初始化完成' AS status;
EOSQL
""", "安装并初始化MySQL")

        # ========== 4. 初始化数据库表 ==========
        print("\n" + "="*50)
        print("[步骤3] 初始化数据库表结构")
        print("="*50)

        fixer.run_script(f"""
mysql -u root team_match < {PROJECT_HOME}/backend/sql/01_init_database.sql 2>/dev/null || echo "库已存在(可忽略)"
mysql -u root team_match < {PROJECT_HOME}/backend/sql/02_create_tables.sql 2>&1
mysql -u root team_match < {PROJECT_HOME}/backend/sql/03_seed_data.sql 2>&1
echo "SQL脚本执行完成"

# 验证表
mysql -u root team_match -e "SHOW TABLES; SELECT COUNT(*) AS table_count FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match';"
""", "执行SQL建表脚本")

        # ========== 5. 配置Nginx站点 ==========
        print("\n" + "="*50)
        print("[步骤4] 配置Nginx站点")
        print("="*50)

        fixer.run_script(f"""
# 确定PHP-FPM socket路径
PHP_SOCK=$(find /run/php/ -name "php*.sock" 2>/dev/null | head -1)
if [ -z "$PHP_SOCK" ]; then
    PHP_SOCK="/run/php/php{php_ver_str}-fpm.sock"
fi
echo "使用PHP socket: $PHP_SOCK"

cat > /etc/nginx/sites-available/teammatch << EONGINX
server {{
    listen 80 default_server;
    server_name 8.138.252.49 _;

    root {PROJECT_HOME};
    index index.html index.php;

    # 前端静态文件
    location / {{
        root {PROJECT_HOME}/frontend;
        try_files \\$uri \\$uri/ /index.html;
    }}

    # 后端API - PHP处理
    location /api/ {{
        alias {PROJECT_HOME}/backend/;
        try_files \\$uri \\$uri/ /backend/index.php?\\$query_string;

        location ~ \\.php\$ {{
            include fastcgi_params;
            fastcgi_pass unix:$PHP_SOCK;
            fastcgi_param SCRIPT_FILENAME \\$request_filename;
            fastcgi_param PATH_INFO \\$fastcgi_path_info;
        }}
    }}

    # 安全：禁止访问隐藏文件
    location ~ /\\. {{
        deny all;
        access_log off;
        log_not_found off;
    }}

    # 安全：禁止访问敏感文件
    location ~ \\.(sql|md|log)\$ {{
        deny all;
    }}

    # Gzip压缩
    gzip on;
    gzip_types text/css application/javascript application/json text/html;
}}
EONGINX

# 启用站点
mkdir -p /etc/nginx/sites-enabled
ln -sf /etc/nginx/sites-available/teammatch /etc/nginx/sites-enabled/teammatch
rm -f /etc/nginx/sites-enabled/default

# 测试配置
nginx -t
systemctl reload nginx || systemctl restart nginx
systemctl enable nginx

echo "Nginx站点配置完成"
""", "配置Nginx站点")

        # ========== 6. 修复PHP-FPM配置 ==========
        print("\n" + "="*50)
        print("[步骤5] 配置PHP-FPM")
        print("="*50)

        fixer.run_script(f"""
# 确保PHP-FPM运行
systemctl start php{php_ver_str}-fpm 2>/dev/null || systemctl start php-fpm 2>/dev/null
systemctl enable php{php_ver_str}-fpm 2>/dev/null || systemctl enable php-fpm 2>/dev/null

# PHP安全配置
PHP_INI="/etc/php/{php_ver_str}/fpm/php.ini"
if [ -f "$PHP_INI" ]; then
    sed -i 's/^;*expose_php.*/expose_php = Off/' "$PHP_INI"
    sed -i 's/^;*display_errors.*/display_errors = Off/' "$PHP_INI"
    sed -i 's/^;*log_errors.*/log_errors = On/' "$PHP_INI"
fi

PHP_CLI_INI="/etc/php/{php_ver_str}/cli/php.ini"
if [ -f "$PHP_CLI_INI" ]; then
    sed -i 's/^;*expose_php.*/expose_php = Off/' "$PHP_CLI_INI"
fi

# 重启PHP-FPM
systemctl restart php{php_ver_str}-fpm 2>/dev/null || systemctl restart php-fpm 2>/dev/null
echo "PHP-FPM配置完成"
""", "配置PHP-FPM")

        # ========== 7. 配置API路由(Nginx重写) ==========
        print("\n" + "="*50)
        print("[步骤6] 配置API路由重写")
        print("="*50)

        # 为Nginx创建API路由配置 - 直接代理到backend/index.php
        fixer.run_script(f"""
PHP_SOCK=$(find /run/php/ -name "php*.sock" 2>/dev/null | head -1)

# 修改 Nginx 配置以正确路由 API
cat > /etc/nginx/sites-available/teammatch << 'EONGINX'
server {{
    listen 80 default_server;
    server_name 8.138.252.49 _;

    root {PROJECT_HOME};
    charset utf-8;
    index index.html index.php;

    # 前端页面
    location / {{
        root {PROJECT_HOME}/frontend;
        try_files $uri $uri/ /index.html;
    }}

    # API接口 - 全部转发到 backend/index.php
    location /api/ {{
        root {PROJECT_HOME};
        rewrite ^/api/(.*)$ /backend/api/$1 last;
    }}

    location /backend/ {{
        root {PROJECT_HOME};
        include fastcgi_params;
        fastcgi_pass unix:{PHP_SOCK};
        fastcgi_param SCRIPT_FILENAME {PROJECT_HOME}/$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
    }}

    # 前端直接访问PHP文件(如backend/index.php)
    location ~ \.php$ {{
        root {PROJECT_HOME};
        include fastcgi_params;
        fastcgi_pass unix:{PHP_SOCK};
        fastcgi_param SCRIPT_FILENAME {PROJECT_HOME}$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
    }}

    # 安全
    location ~ /\. {{
        deny all;
    }}

    location ~ \\.(sql|md|log)$ {{
        deny all;
    }}

    gzip on;
    gzip_types text/css application/javascript application/json text/html;
}}
EONGINX

nginx -t
systemctl reload nginx
echo "Nginx路由配置完成"
""", "配置API路由")

        # ========== 8. 修复文件权限 ==========
        print("\n" + "="*50)
        print("[步骤7] 修复文件权限")
        print("="*50)

        fixer.run_script(f"""
# 修正所有权
chown -R teammatch:teammatch {PROJECT_HOME}
chmod -R 755 {PROJECT_HOME}
chmod -R 775 {PROJECT_HOME}/backend/uploads
chmod -R 775 {PROJECT_HOME}/logs

# 确保Nginx用户能访问
usermod -a -G teammatch www-data 2>/dev/null || true

echo "权限配置完成"
ls -la {PROJECT_HOME}/
""", "修复权限")

        # ========== 9. 全面验证 ==========
        print("\n" + "="*50)
        print("[步骤8] 全面验证")
        print("="*50)

        fixer.run_script("""
echo "============ 1. 服务状态 ============"
for svc in nginx mysql php8.4-fpm sshd; do
    status=$(systemctl is-active $svc 2>/dev/null || echo "inactive")
    echo "  $svc: $status"
done

echo ""
echo "============ 2. 端口监听 ============"
ss -tlnp | grep -E ':(22|80|3306) '

echo ""
echo "============ 3. 数据库表验证 ============"
mysql -u root team_match -e "SELECT COUNT(*) AS total_tables FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match';" 2>/dev/null
mysql -u root team_match -e "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match' ORDER BY TABLE_NAME;" 2>/dev/null

echo ""
echo "============ 4. HTTP测试 ============"
echo "前端首页:"
curl -s -o /dev/null -w 'HTTP %{http_code} Size:%{size_download}B\\n' http://localhost/

echo "API测试:"
curl -s -w '\\nHTTP %{http_code}' http://localhost/api/courses 2>/dev/null | head -5

echo ""
echo "============ 5. PHP信息 ============"
php -v 2>&1 | head -1
php -m 2>/dev/null | grep -i pdo

echo ""
echo "============ 6. 防火墙 ============"
ufw status | head -15
""", "全面验证")

        # ========== 10. 检查Nginx错误 ==========
        print("\n" + "="*50)
        print("[步骤9] 诊断Nginx配置")
        print("="*50)

        fixer.run_script("""
echo "=== Nginx配置测试 ==="
nginx -t 2>&1

echo ""
echo "=== Nginx错误日志 ==="
tail -20 /var/log/nginx/error.log 2>/dev/null || echo "无错误日志"

echo ""
echo "=== 测试PHP解析 ==="
echo '<?php echo "PHP_OK";' > /tmp/test.php
curl -s http://localhost/test.php 2>/dev/null
rm -f /tmp/test.php

echo ""
echo "=== 测试API路由 ==="
curl -s http://localhost/api/courses 2>/dev/null | head -200
""", "诊断Nginx")

    finally:
        fixer.close()

    print("\n[DONE] 环境修复完成")


if __name__ == '__main__':
    main()
