#!/bin/bash
# ============================================================
# TeamMatch 服务器恢复与部署完成脚本
# 请在云服务商VNC控制台(阿里云ECS管理终端)中执行此脚本
# ============================================================

set -e
PROJECT_HOME="/opt/teammatch"
echo "[INFO] TeamMatch 环境修复与部署完成脚本"
echo "[INFO] 执行时间: $(date '+%Y-%m-%d %H:%M:%S')"

# ============================================================
# 第一步：恢复SSH访问并添加本地开发密钥
# ============================================================
echo ""
echo "=========================================="
echo " [步骤1] SSH配置恢复 + 添加本地部署密钥"
echo "=========================================="
sed -i 's/^PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
# 添加本地开发机的SSH公钥
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF9p9+5v18WAINlDUncKo0ZUVk7JSoF7wJqvUDxj/rw2 teammatch-local-deploy' >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
systemctl restart sshd
echo "[OK] SSH root密码登录已恢复，本地部署密钥已添加"

# ============================================================
# 第二步：停用Apache2，安装配置Nginx
# ============================================================
echo ""
echo "=========================================="
echo " [步骤2] 停用Apache2，安装Nginx"
echo "=========================================="
export DEBIAN_FRONTEND=noninteractive
systemctl stop apache2 2>/dev/null || true
systemctl disable apache2 2>/dev/null || true
apt-get remove -y -qq apache2 apache2-bin apache2-data apache2-utils 2>/dev/null || true
apt-get install -y -qq nginx
systemctl start nginx && systemctl enable nginx
echo "[OK] Nginx安装完成"

# ============================================================
# 第三步：安装PHP-FPM及扩展
# ============================================================
echo ""
echo "=========================================="
echo " [步骤3] 安装PHP-FPM及扩展"
echo "=========================================="
apt-get install -y -qq php8.4-fpm php8.4-mysql php8.4-mbstring php8.4-xml php8.4-curl php8.4-gd php8.4-zip 2>/dev/null || \
apt-get install -y -qq php-fpm php-mysql php-mbstring php-xml php-curl php-gd php-zip 2>/dev/null
PHP_SOCK=$(find /run/php/ -name "php*.sock" 2>/dev/null | head -1)
echo "[OK] PHP-FPM安装完成, socket: $PHP_SOCK"

# 确保服务运行
PHP_FPM_SVC=$(systemctl list-unit-files | grep php.*fpm | awk '{print $1}' | head -1)
if [ -n "$PHP_FPM_SVC" ]; then
    systemctl start "$PHP_FPM_SVC" 2>/dev/null || true
    systemctl enable "$PHP_FPM_SVC" 2>/dev/null || true
fi
echo "[OK] PHP-FPM服务已启动: $PHP_FPM_SVC"

# ============================================================
# 第四步：安装配置MySQL
# ============================================================
echo ""
echo "=========================================="
echo " [步骤4] 安装配置MySQL"
echo "=========================================="
apt-get install -y -qq mysql-server
systemctl start mysql 2>/dev/null || true
systemctl enable mysql 2>/dev/null || true

# 初始化数据库和用户
mysql -u root << 'EOSQL'
CREATE DATABASE IF NOT EXISTS team_match DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'teammatch'@'localhost' IDENTIFIED BY 'Tm@2024#Secure';
GRANT ALL PRIVILEGES ON team_match.* TO 'teammatch'@'localhost';
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Root@Tm#2024#Admin';
FLUSH PRIVILEGES;
SELECT 'MySQL初始化完成' AS result;
EOSQL
echo "[OK] MySQL安装配置完成"

# ============================================================
# 第五步：初始化数据库表结构
# ============================================================
echo ""
echo "=========================================="
echo " [步骤5] 初始化数据库表"
echo "=========================================="
mysql -u root team_match < ${PROJECT_HOME}/backend/sql/02_create_tables.sql 2>&1 && echo "  -> 建表完成"
mysql -u root team_match < ${PROJECT_HOME}/backend/sql/03_seed_data.sql 2>&1 && echo "  -> 测试数据插入完成"
mysql -u root team_match -e "SHOW TABLES;"
TABLE_COUNT=$(mysql -u root -N -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match';")
echo "[OK] 数据库初始化完成，共 ${TABLE_COUNT} 张表"

# ============================================================
# 第六步：配置Nginx站点
# ============================================================
echo ""
echo "=========================================="
echo " [步骤6] 配置Nginx站点"
echo "=========================================="
PHP_SOCK=$(find /run/php/ -name "php*.sock" 2>/dev/null | head -1)
[ -z "$PHP_SOCK" ] && PHP_SOCK="/run/php/php8.4-fpm.sock"

mkdir -p /etc/nginx/sites-enabled

cat > /etc/nginx/sites-available/teammatch << EONGINX
server {
    listen 80 default_server;
    server_name 8.138.252.49 _;

    root ${PROJECT_HOME};
    charset utf-8;
    index index.html index.php;

    # 前端页面
    location / {
        root ${PROJECT_HOME}/frontend;
        try_files \$uri \$uri/ /index.html;
    }

    # API接口重写到backend
    location /api/ {
        root ${PROJECT_HOME};
        rewrite ^/api/(.*)\$ /backend/api/\$1 last;
    }

    # PHP处理(backend目录)
    location /backend/ {
        root ${PROJECT_HOME};
        include fastcgi_params;
        fastcgi_pass unix:${PHP_SOCK};
        fastcgi_param SCRIPT_FILENAME ${PROJECT_HOME}\$fastcgi_script_name;
        fastcgi_param PATH_INFO \$fastcgi_path_info;
    }

    # 通用PHP处理
    location ~ \.php\$ {
        root ${PROJECT_HOME};
        include fastcgi_params;
        fastcgi_pass unix:${PHP_SOCK};
        fastcgi_param SCRIPT_FILENAME ${PROJECT_HOME}\$fastcgi_script_name;
        fastcgi_param PATH_INFO \$fastcgi_path_info;
    }

    # 安全禁止
    location ~ /\. { deny all; }
    location ~ \.(sql|md|log)\$ { deny all; }

    # Gzip
    gzip on;
    gzip_types text/css application/javascript application/json text/html;
}
EONGINX

ln -sf /etc/nginx/sites-available/teammatch /etc/nginx/sites-enabled/teammatch
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
echo "[OK] Nginx站点配置完成"

# ============================================================
# 第七步：PHP安全配置
# ============================================================
echo ""
echo "=========================================="
echo " [步骤7] PHP安全配置"
echo "=========================================="
PHP_VER=$(php -v 2>/dev/null | head -1 | grep -oP '\d+\.\d+' | head -1)
echo "PHP版本: $PHP_VER"
for ini in /etc/php/${PHP_VER}/fpm/php.ini /etc/php/${PHP_VER}/cli/php.ini; do
    if [ -f "$ini" ]; then
        sed -i 's/^;*expose_php.*/expose_php = Off/' "$ini"
        sed -i 's/^;*display_errors.*/display_errors = Off/' "$ini"
        sed -i 's/^;*log_errors.*/log_errors = On/' "$ini"
        echo "  -> 已更新: $ini"
    fi
done

# 重启PHP-FPM
PHP_FPM_SVC=$(systemctl list-unit-files | grep php.*fpm | awk '{print $1}' | head -1)
[ -n "$PHP_FPM_SVC" ] && systemctl restart "$PHP_FPM_SVC"
echo "[OK] PHP安全配置完成"

# ============================================================
# 第八步：修复文件权限
# ============================================================
echo ""
echo "=========================================="
echo " [步骤8] 文件权限修正"
echo "=========================================="
chown -R teammatch:teammatch ${PROJECT_HOME}
chmod -R 755 ${PROJECT_HOME}
chmod -R 775 ${PROJECT_HOME}/backend/uploads 2>/dev/null || true
chmod -R 775 ${PROJECT_HOME}/logs 2>/dev/null || true
usermod -a -G teammatch www-data 2>/dev/null || true
echo "[OK] 权限配置完成"

# ============================================================
# 第九步：设置SSH密钥认证（永久安全方案）
# ============================================================
echo ""
echo "=========================================="
echo " [步骤9] 配置SSH密钥认证"
echo "=========================================="

# 为root生成authorized_keys
cat /root/.ssh/teammatch_server.pub >> /root/.ssh/authorized_keys 2>/dev/null || true
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys
# 显示私钥以便复制到本地
echo ""
echo "=========== 请复制以下私钥到本地 ==========="
echo "保存路径: ~/.ssh/teammatch_server (Linux/Mac) 或 %USERPROFILE%\.ssh\teammatch_server (Windows)"
echo "权限: chmod 600 (Linux/Mac)"
echo "============================================"
cat /root/.ssh/teammatch_server
echo ""
echo "=========== 私钥内容结束 ==========="
echo ""

# 启用root密钥登录（禁用密码）
sed -i 's/^PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
grep -q '^PasswordAuthentication' /etc/ssh/sshd_config || echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config
sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
echo "[OK] SSH密钥认证已配置，密码登录已禁用"

# ============================================================
# 第十步：全面验证测试
# ============================================================
echo ""
echo "=========================================="
echo " [步骤10] 全面验证测试"
echo "=========================================="

echo ""
echo "--- 1. 服务运行状态 ---"
for svc in nginx mysql; do
    status=$(systemctl is-active $svc 2>/dev/null || echo "inactive")
    echo "  $svc: $status"
done
PHP_FPM_SVC=$(systemctl list-unit-files | grep php.*fpm | awk '{print $1}' | head -1)
status=$(systemctl is-active "$PHP_FPM_SVC" 2>/dev/null || echo "inactive")
echo "  $PHP_FPM_SVC: $status"
echo "  sshd: $(systemctl is-active sshd)"

echo ""
echo "--- 2. 端口监听 ---"
ss -tlnp | grep -E ':(22|80|3306) ' || netstat -tlnp | grep -E ':(22|80|3306) '

echo ""
echo "--- 3. 防火墙状态 ---"
ufw status | head -15

echo ""
echo "--- 4. 软件版本 ---"
php -v 2>&1 | head -1
mysql --version 2>&1
nginx -v 2>&1
python3 --version

echo ""
echo "--- 5. 数据库验证 ---"
mysql -u root team_match -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='team_match' ORDER BY TABLE_NAME;"

echo ""
echo "--- 6. HTTP访问测试 ---"
echo "前端首页:"
curl -s -o /dev/null -w "  HTTP %{http_code} Size:%{size_download}B\n" http://localhost/
echo "API接口:"
curl -s http://localhost/api/courses | python3 -m json.tool 2>/dev/null | head -20 || curl -s http://localhost/api/courses | head -20
echo ""

echo ""
echo "--- 7. 外网访问测试 ---"
curl -s -o /dev/null -w "  HTTP %{http_code}\n" http://8.138.252.49/

echo ""
echo "=========================================="
echo " [DONE] TeamMatch 服务器部署完成!"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  前端首页:    http://8.138.252.49/"
echo "  管理后台:    http://8.138.252.49/admin.html"
echo "  API接口:     http://8.138.252.49/api/courses"
echo "  智能推荐:    http://8.138.252.49/recommend.html"
echo ""
echo "管理员账号: admin001 / 123456"
echo "数据库root密码: Root@Tm#2024#Admin"
echo "项目用户: teammatch / 密码未设置(仅密钥登录)"
echo ""
echo "SSH私钥已显示在上方，请保存到本地并使用:"
echo "  ssh -i ~/.ssh/teammatch_server root@8.138.252.49"
