#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeamMatch 远程服务器环境部署脚本
服务器: 8.138.252.49
功能: 安全加固 + 环境安装 + 权限管理 + 项目部署 + 验证测试
"""
import paramiko
import os
import sys
import time
import json

# ========== 配置区 ==========
HOST = '8.138.252.49'
PORT = 22
USER = 'root'
PASSWORD = 'admin12345789@'
PROJECT_USER = 'teammatch'
PROJECT_HOME = '/opt/teammatch'
SSH_KEY_FILE = os.path.expanduser('~/.ssh/teammatch_deploy')
# ============================

class RemoteDeployer:
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.client = None

    def connect(self):
        """建立SSH连接"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"[连接] 正在连接 {self.user}@{self.host}:{self.port} ...")
        self.client.connect(self.host, self.port, self.user, self.password, timeout=30)
        print(f"[连接] [OK] 已连接到 {self.host}")
        return self

    def close(self):
        if self.client:
            self.client.close()

    def exec(self, cmd, desc='', sudo=False, silent=False):
        """执行远程命令并返回结果"""
        if sudo and self.user != 'root':
            cmd = f"sudo {cmd}"
        label = desc or cmd[:60]
        if not silent:
            print(f"[执行] {label}...")
        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=120)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if err and 'WARNING' not in err and not silent:
            print(f"  STDERR: {err[:200]}")
        if out and not silent:
            for line in out.split('\n')[:20]:
                print(f"  {line}")
        return out, err

    def exec_script(self, script, desc=''):
        """通过 bash 执行多行脚本"""
        label = desc or script[:60]
        print(f"[脚本] {label}...")
        # 使用 heredoc 方式传入脚本
        stdin, stdout, stderr = self.client.exec_command(
            f"bash -s << 'SCRIPT_EOF'\n{script}\nSCRIPT_EOF", timeout=300
        )
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if err:
            # 过滤掉非错误信息
            lines = [l for l in err.split('\n') if 'WARNING' not in l and 'Warning' not in l]
            if lines:
                print(f"  STDERR: {'; '.join(lines)[:300]}")
        if out:
            for line in out.split('\n')[:30]:
                print(f"  {line}")
        return out, err

    def put_file(self, local_path, remote_path):
        """上传文件到服务器"""
        print(f"[上传] {local_path} -> {remote_path}")
        sftp = self.client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.chmod(remote_path, 0o644)
        sftp.close()

    def put_dir(self, local_dir, remote_dir):
        """上传整个目录"""
        print(f"[上传目录] {local_dir} -> {remote_dir}")
        # 先创建远程目录
        self.exec(f"mkdir -p '{remote_dir}'")
        sftp = self.client.open_sftp()
        for root, dirs, files in os.walk(local_dir):
            rel_root = os.path.relpath(root, local_dir)
            remote_root = os.path.join(remote_dir, rel_root).replace('\\', '/')
            for d in dirs:
                try:
                    sftp.mkdir(os.path.join(remote_root, d).replace('\\', '/'))
                except:
                    pass
            for f in files:
                local_f = os.path.join(root, f)
                remote_f = os.path.join(remote_root, f).replace('\\', '/')
                try:
                    sftp.put(local_f, remote_f)
                    sftp.chmod(remote_f, 0o644)
                except Exception as e:
                    print(f"  [WARN] 上传失败 {f}: {e}")
        sftp.close()


# ==================== 部署步骤 ====================

def step1_detect(deployer):
    """步骤1: 探测服务器环境"""
    print("\n" + "="*60)
    print("【步骤1】探测服务器环境")
    print("="*60)

    deployer.exec("cat /etc/os-release", "OS版本")
    deployer.exec("uname -a", "内核信息")
    deployer.exec("free -h", "内存信息")
    deployer.exec("df -h", "磁盘信息")
    deployer.exec("cat /proc/cpuinfo | grep 'model name' | head -1", "CPU型号")
    deployer.exec("ss -tlnp || netstat -tlnp", "当前监听端口")
    deployer.exec("which php mysql nginx python3 git node npm 2>/dev/null || echo '有些工具未安装'", "已有工具")
    deployer.exec("getenforce 2>/dev/null || echo 'SELinux not available'", "SELinux状态")

    # 判断操作系统类型
    out, _ = deployer.exec("cat /etc/os-release", silent=True)
    os_type = 'unknown'
    if 'Ubuntu' in out:
        os_type = 'ubuntu'
    elif 'CentOS' in out or 'Rocky' in out or 'Alma' in out:
        os_type = 'centos'
    elif 'Debian' in out:
        os_type = 'debian'

    return os_type


def step2_security(deployer, os_type):
    """步骤2: 安全加固"""
    print("\n" + "="*60)
    print("【步骤2】安全加固")
    print("="*60)

    # 根据OS类型选择包管理器
    pkg_cmd = 'apt-get' if os_type in ('ubuntu', 'debian') else 'yum'

    # 2.1 系统更新
    print("\n--- 2.1 系统安全更新 ---")
    if os_type in ('ubuntu', 'debian'):
        deployer.exec("export DEBIAN_FRONTEND=noninteractive && apt-get update -qq && apt-get upgrade -y -qq", "系统包更新")
    else:
        deployer.exec("yum update -y --quiet", "系统包更新")

    # 2.2 安装并配置防火墙
    print("\n--- 2.2 防火墙配置 ---")
    if os_type in ('ubuntu', 'debian'):
        deployer.exec("apt-get install -y -qq ufw", "安装UFW防火墙")
        deployer.exec_script("""
ufw --force disable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP
ufw allow 443/tcp    # HTTPS
ufw allow 8080/tcp   # 备用端口
ufw --force enable
ufw status verbose
""", "配置UFW规则")
    else:
        deployer.exec("yum install -y firewalld && systemctl start firewalld && systemctl enable firewalld", "安装firewalld")
        deployer.exec_script("""
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload
firewall-cmd --list-all
""", "配置firewalld规则")

    # 2.3 SSH安全加固
    print("\n--- 2.3 SSH安全加固 ---")
    # 备份原配置
    deployer.exec("cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d)", "备份SSH配置")

    # 修改SSH配置
    deployer.exec_script("""
# 禁用root密码登录，禁用空密码
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*PermitEmptyPasswords.*/PermitEmptyPasswords no/' /etc/ssh/sshd_config
sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/^#*ClientAliveInterval.*/ClientAliveInterval 300/' /etc/ssh/sshd_config
sed -i 's/^#*ClientAliveCountMax.*/ClientAliveCountMax 2/' /etc/ssh/sshd_config

# 确保这些配置存在（如果不存在则追加）
grep -q '^PermitRootLogin' /etc/ssh/sshd_config || echo 'PermitRootLogin prohibit-password' >> /etc/ssh/sshd_config
grep -q '^PermitEmptyPasswords' /etc/ssh/sshd_config || echo 'PermitEmptyPasswords no' >> /etc/ssh/sshd_config
grep -q '^X11Forwarding' /etc/ssh/sshd_config || echo 'X11Forwarding no' >> /etc/ssh/sshd_config
grep -q '^MaxAuthTries' /etc/ssh/sshd_config || echo 'MaxAuthTries 3' >> /etc/ssh/sshd_config

echo "SSH配置已更新，主要变更："
grep -E '^(PermitRootLogin|PasswordAuthentication|PermitEmptyPasswords|X11Forwarding|MaxAuthTries|ClientAliveInterval)' /etc/ssh/sshd_config
""", "修改SSH安全配置")

    # 重启SSH服务
    deployer.exec("sshd -t && systemctl restart sshd || service ssh restart", "重启SSH服务")

    # 2.4 生成部署用SSH密钥
    print("\n--- 2.4 部署用SSH密钥 ---")
    deployer.exec("mkdir -p ~/.ssh && chmod 700 ~/.ssh", "创建SSH目录")
    deployer.exec("ssh-keygen -t ed25519 -f ~/.ssh/teammatch_server -N '' -C 'teammatch-deploy' 2>/dev/null && echo '密钥生成成功' || echo '密钥已存在或生成失败'", "生成服务器端SSH密钥")

    # 2.5 禁用不必要服务
    print("\n--- 2.5 禁用不必要服务 ---")
    deployer.exec_script("""
for svc in rpcbind rpcbind.socket avahi-daemon cups bluetooth; do
    if systemctl list-unit-files "$svc" 2>/dev/null | grep -q "$svc"; then
        systemctl stop "$svc" 2>/dev/null
        systemctl disable "$svc" 2>/dev/null
        echo "已禁用: $svc"
    fi
done
echo "不必要服务已禁用"
""", "禁用不必要服务")

    print("\n[OK] 安全加固完成")


def step3_environment(deployer, os_type):
    """步骤3: 安装运行时环境"""
    print("\n" + "="*60)
    print("【步骤3】安装运行时环境")
    print("="*60)

    if os_type in ('ubuntu', 'debian'):
        deployer.exec("export DEBIAN_FRONTEND=noninteractive", "设置非交互模式")

        # 添加PHP PPA以获取最新PHP版本
        deployer.exec_script("""
apt-get install -y -qq software-properties-common apt-transport-https ca-certificates curl
add-apt-repository -y ppa:ondrej/php 2>/dev/null || echo "PPA添加失败，使用系统默认源"
apt-get update -qq
""", "添加PHP PPA源")

        # 安装所有必需组件
        deployer.exec_script("""
apt-get install -y -qq \\
    nginx \\
    mysql-server \\
    php8.1 \\
    php8.1-fpm \\
    php8.1-mysql \\
    php8.1-mbstring \\
    php8.1-xml \\
    php8.1-json \\
    php8.1-curl \\
    php8.1-gd \\
    php8.1-zip \\
    python3 \\
    python3-pip \\
    git \\
    curl \\
    wget \\
    unzip \\
    2>&1 || echo "部分php8.1包不可用，尝试php8.0"
""", "安装Nginx+MySQL+PHP+Python+Git")

        # 如果php8.1不可用，尝试php8.0或php
        deployer.exec_script("""
# 检查PHP是否安装成功
if ! command -v php &> /dev/null; then
    echo "尝试安装php8.0..."
    apt-get install -y -qq php8.0 php8.0-fpm php8.0-mysql php8.0-mbstring php8.0-xml php8.0-json php8.0-curl php8.0-gd php8.0-zip 2>&1 || \
    apt-get install -y -qq php php-fpm php-mysql php-mbstring php-xml php-json php-curl php-gd php-zip 2>&1
fi
php -v || echo "PHP安装可能失败，请手动检查"
""", "PHP版本兼容性处理")

    else:
        # CentOS/RHEL
        deployer.exec_script("""
# 安装EPEL和Remi仓库
yum install -y epel-release
yum install -y https://rpms.remirepo.net/enterprise/remi-release-8.rpm 2>/dev/null || \
yum install -y https://rpms.remirepo.net/enterprise/remi-release-7.rpm 2>/dev/null || echo "Remi仓库添加失败"
yum module reset php -y 2>/dev/null || echo "PHP模块重置跳过"
yum module enable php:8.1 -y 2>/dev/null || echo "PHP 8.1模块不可用"
""", "配置CentOS仓库")

        deployer.exec_script("""
yum install -y \\
    nginx \\
    mysql-server \\
    php \\
    php-fpm \\
    php-mysqlnd \\
    php-mbstring \\
    php-xml \\
    php-json \\
    php-curl \\
    php-gd \\
    php-zip \\
    python3 \\
    python3-pip \\
    git \\
    curl \\
    wget \\
    unzip
""", "安装所有服务")

    # 启动并启用服务
    print("\n--- 启动各项服务 ---")
    deployer.exec_script("""
# 启动MySQL
if systemctl list-unit-files mysqld 2>/dev/null | grep -q mysqld; then
    systemctl start mysqld && systemctl enable mysqld
elif systemctl list-unit-files mysql 2>/dev/null | grep -q mysql; then
    systemctl start mysql && systemctl enable mysql
fi

# 启动PHP-FPM
if systemctl list-unit-files php8.1-fpm 2>/dev/null | grep -q php8.1-fpm; then
    systemctl start php8.1-fpm && systemctl enable php8.1-fpm
elif systemctl list-unit-files php-fpm 2>/dev/null | grep -q php-fpm; then
    systemctl start php-fpm && systemctl enable php-fpm
fi

# 启动Nginx
if systemctl list-unit-files nginx 2>/dev/null | grep -q nginx; then
    systemctl start nginx && systemctl enable nginx
fi

echo "服务状态:"
systemctl is-active nginx mysqld mysql php8.1-fpm php-fpm 2>/dev/null || \
service nginx status 2>/dev/null; service mysql status 2>/dev/null
""", "启动所有服务")

    # 初始化MySQL安全配置
    print("\n--- MySQL安全初始化 ---")
    deployer.exec_script("""
# 获取MySQL临时密码（如果有）
TEMP_PWD=""
if [ -f /var/log/mysqld.log ]; then
    TEMP_PWD=$(grep 'temporary password' /var/log/mysqld.log 2>/dev/null | awk '{print $NF}' | tail -1)
fi

# 尝试无密码登录（Ubuntu/Debian auth_socket）
if mysql -u root -e "SELECT 1" 2>/dev/null; then
    echo "MySQL root 可通过 socket 直接登录"
    mysql -u root << 'EOSQL'
-- 创建项目数据库
CREATE DATABASE IF NOT EXISTS team_match DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 创建项目专用用户
CREATE USER IF NOT EXISTS 'teammatch'@'localhost' IDENTIFIED BY 'Tm@2024#Secure';
GRANT ALL PRIVILEGES ON team_match.* TO 'teammatch'@'localhost';
-- 设置root密码
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Root@Tm#2024#Admin';
FLUSH PRIVILEGES;
SELECT '[OK] MySQL初始化完成' AS status;
EOSQL
elif [ -n "$TEMP_PWD" ]; then
    # 使用临时密码登录并修改
    mysql -u root -p"$TEMP_PWD" --connect-expired-password << 'EOSQL' 2>/dev/null
ALTER USER 'root'@'localhost' IDENTIFIED BY 'Root@Tm#2024#Admin';
CREATE DATABASE IF NOT EXISTS team_match DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'teammatch'@'localhost' IDENTIFIED BY 'Tm@2024#Secure';
GRANT ALL PRIVILEGES ON team_match.* TO 'teammatch'@'localhost';
FLUSH PRIVILEGES;
SELECT '[OK] MySQL初始化完成' AS status;
EOSQL
else
    echo "[WARN] 无法自动配置MySQL，请手动执行 mysql_secure_installation"
fi
""", "MySQL数据库初始化")

    print("\n[OK] 环境安装完成")


def step4_permissions(deployer, os_type):
    """步骤4: 权限管理"""
    print("\n" + "="*60)
    print("【步骤4】权限管理")
    print("="*60)

    # 4.1 创建项目用户
    print("\n--- 4.1 创建项目用户 ---")
    deployer.exec_script(f"""
# 创建专用用户和组
if id "{PROJECT_USER}" &>/dev/null; then
    echo "用户 {PROJECT_USER} 已存在"
else
    useradd -r -m -d {PROJECT_HOME} -s /bin/bash {PROJECT_USER}
    echo "用户 {PROJECT_USER} 已创建"
fi

# 将用户加入必要组
usermod -a -G www-data {PROJECT_USER} 2>/dev/null || \
usermod -a -G nginx {PROJECT_USER} 2>/dev/null || \
echo "已添加到web组"

# 为项目用户生成SSH密钥
su - {PROJECT_USER} -c "ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N '' -C '{PROJECT_USER}@teammatch' 2>/dev/null && echo 'SSH密钥已生成' || echo 'SSH密钥可能已存在'"

# 设置sudo权限（仅允许重启Web服务）
echo "{PROJECT_USER} ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx, /usr/bin/systemctl restart php*-fpm, /usr/bin/systemctl restart mysql" > /etc/sudoers.d/{PROJECT_USER}
chmod 440 /etc/sudoers.d/{PROJECT_USER}
echo "Sudo权限已配置"
""", "创建项目用户")

    # 4.2 创建项目目录结构
    print("\n--- 4.2 创建项目目录 ---")
    deployer.exec_script(f"""
mkdir -p {PROJECT_HOME}/{{backend,frontend,logs,sessions}}
mkdir -p {PROJECT_HOME}/backend/{{api,config,model,service,middleware,util,sql,uploads}}
chown -R {PROJECT_USER}:{PROJECT_USER} {PROJECT_HOME}
chmod -R 755 {PROJECT_HOME}
# 确保上传目录和日志目录可写
chmod -R 775 {PROJECT_HOME}/backend/uploads
chmod -R 775 {PROJECT_HOME}/logs
chmod -R 775 {PROJECT_HOME}/sessions
echo "项目目录已创建"
ls -la {PROJECT_HOME}/
""", "创建项目目录")

    # 4.3 配置文件权限
    print("\n--- 4.3 配置文件权限 ---")
    deployer.exec_script("""
# PHP-FPM 配置：PHP session 安全
PHP_INI=$(php -i 2>/dev/null | grep 'Loaded Configuration File' | awk '{print $NF}' | head -1)
if [ -f "$PHP_INI" ]; then
    # 安全PHP配置
    sed -i 's/^;*expose_php.*/expose_php = Off/' "$PHP_INI"
    sed -i 's/^;*display_errors.*/display_errors = Off/' "$PHP_INI"
    sed -i 's/^;*log_errors.*/log_errors = On/' "$PHP_INI"
    echo "PHP安全配置已更新: $PHP_INI"
fi
""", "PHP安全配置")

    print("\n[OK] 权限管理完成")


def step5_deploy(deployer):
    """步骤5: 部署项目代码"""
    print("\n" + "="*60)
    print("【步骤5】部署项目代码")
    print("="*60)

    # 上传项目文件（需要本地文件路径）
    project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    project_root = os.path.abspath(project_root)

    print(f"\n项目根目录: {project_root}")

    # 检查本地文件
    if not os.path.exists(os.path.join(project_root, 'backend')):
        print(f"[ERROR] 找不到 backend 目录: {project_root}/backend")
        print("请确认脚本放置在正确位置")
        return False

    # 上传后端
    print("\n--- 5.1 上传后端代码 ---")
    deployer.put_dir(
        os.path.join(project_root, 'backend'),
        f'{PROJECT_HOME}/backend'
    )

    # 上传前端
    print("\n--- 5.2 上传前端代码 ---")
    deployer.put_dir(
        os.path.join(project_root, 'frontend'),
        f'{PROJECT_HOME}/frontend'
    )

    # 5.3 配置数据库连接
    print("\n--- 5.3 配置后端数据库连接 ---")
    deployer.exec_script(f"""
cat > {PROJECT_HOME}/backend/config/database.php << 'EOPHP'
<?php
return [
    'host'     => '127.0.0.1',
    'port'     => 3306,
    'dbname'   => 'team_match',
    'username' => 'teammatch',
    'password' => 'Tm@2024#Secure',
    'charset'  => 'utf8mb4',
];
EOPHP
echo "数据库配置已更新"
""", "更新数据库配置")

    # 5.4 执行SQL建库脚本
    print("\n--- 5.4 初始化数据库表结构 ---")
    deployer.exec_script(f"""
# 执行SQL脚本
mysql -u teammatch -p'Tm@2024#Secure' team_match < {PROJECT_HOME}/backend/sql/01_init_database.sql 2>/dev/null || echo "库已存在"
mysql -u teammatch -p'Tm@2024#Secure' team_match < {PROJECT_HOME}/backend/sql/02_create_tables.sql 2>&1
mysql -u teammatch -p'Tm@2024#Secure' team_match < {PROJECT_HOME}/backend/sql/03_seed_data.sql 2>&1
echo "数据库初始化完成"

# 验证表结构
mysql -u teammatch -p'Tm@2024#Secure' team_match -e "SHOW TABLES;"
""", "执行SQL初始化脚本")

    # 5.5 配置Nginx站点
    print("\n--- 5.5 配置Nginx站点 ---")
    deployer.exec(f"""
cat > /etc/nginx/sites-available/teammatch << 'EONGINX'
server {{
    listen 80 default_server;
    server_name 8.138.252.49 _;

    root {PROJECT_HOME};
    index index.html index.php;

    # 前端静态文件
    location / {{
        root {PROJECT_HOME}/frontend;
        try_files $uri $uri/ /index.html;
    }}

    # 后端API
    location /api/ {{
        alias {PROJECT_HOME}/backend/;
        try_files $uri $uri/ /backend/index.php?$query_string;
    }}

    # PHP处理
    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $request_filename;
    }}

    # 安全：禁止访问隐藏文件
    location ~ /\. {{
        deny all;
        access_log off;
        log_not_found off;
    }}

    # 安全：禁止访问敏感文件
    location ~ \\.(sql|md|log)$ {{
        deny all;
    }}

    # Gzip压缩
    gzip on;
    gzip_types text/css application/javascript application/json;
}}
EONGINX

# 启用站点
if [ -d /etc/nginx/sites-enabled ]; then
    ln -sf /etc/nginx/sites-available/teammatch /etc/nginx/sites-enabled/teammatch
    rm -f /etc/nginx/sites-enabled/default
elif [ -d /etc/nginx/conf.d ]; then
    cp /etc/nginx/sites-available/teammatch /etc/nginx/conf.d/teammatch.conf
fi

nginx -t && systemctl reload nginx || service nginx reload
echo "Nginx站点配置完成"
""", "配置Nginx站点")

    # 5.6 更新项目所有权
    deployer.exec(f"chown -R {PROJECT_USER}:{PROJECT_USER} {PROJECT_HOME}", "更新文件所有权")

    print("\n[OK] 项目部署完成")
    return True


def step6_verify(deployer):
    """步骤6: 验证测试"""
    print("\n" + "="*60)
    print("【步骤6】验证测试")
    print("="*60)

    results = {}

    # 6.1 验证软件版本
    print("\n--- 6.1 软件版本验证 ---")
    for cmd, label in [('php -v', 'PHP'), ('mysql --version', 'MySQL'),
                       ('nginx -v 2>&1', 'Nginx'), ('python3 --version', 'Python3'),
                       ('git --version', 'Git')]:
        out, _ = deployer.exec(cmd, f"验证{label}")
        results[label] = out.split('\n')[0] if out else '未安装'

    # 6.2 验证服务状态
    print("\n--- 6.2 服务运行状态 ---")
    for svc in ['nginx', 'mysql', 'php8.1-fpm', 'php-fpm', 'sshd']:
        out, _ = deployer.exec(f"systemctl is-active {svc} 2>/dev/null || echo inactive", f"检查{svc}")
        results[f'service_{svc}'] = out.strip()

    # 6.3 验证防火墙
    print("\n--- 6.3 防火墙状态 ---")
    out, _ = deployer.exec("ufw status 2>/dev/null || firewall-cmd --list-all 2>/dev/null || echo '防火墙未配置'", "防火墙状态")
    results['firewall'] = out[:300]

    # 6.4 验证端口监听
    print("\n--- 6.4 端口监听状态 ---")
    out, _ = deployer.exec("ss -tlnp | grep -E ':(22|80|443|8080|3306) ' || netstat -tlnp | grep -E ':(22|80|443|8080|3306) '", "端口监听")
    results['ports'] = out[:200]

    # 6.5 HTTP访问测试
    print("\n--- 6.5 HTTP访问测试 ---")
    out, _ = deployer.exec("curl -s -o /dev/null -w '%{http_code}' http://localhost/ 2>/dev/null || echo 'FAIL'", "HTTP状态码")
    results['http_status'] = out.strip()

    out, _ = deployer.exec("curl -s http://localhost/api/courses 2>/dev/null | head -200", "API课程接口")
    results['api_courses'] = out[:200]

    # 6.6 SSH安全验证
    print("\n--- 6.6 SSH安全配置验证 ---")
    out, _ = deployer.exec("grep -E '^(PermitRootLogin|PasswordAuthentication|PermitEmptyPasswords|MaxAuthTries|X11Forwarding)' /etc/ssh/sshd_config 2>/dev/null", "SSH配置检查")
    results['ssh_config'] = out

    # 6.7 数据库验证
    print("\n--- 6.7 数据库验证 ---")
    out, _ = deployer.exec("mysql -u teammatch -p'Tm@2024#Secure' team_match -e 'SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema=\"team_match\";' 2>/dev/null", "数据库表数量")
    results['db_tables'] = out

    return results


def generate_report(results, os_type):
    """生成部署报告"""
    print("\n" + "="*60)
    print("【部署报告】")
    print("="*60)

    report = f"""
## TeamMatch 服务器部署报告

### 服务器信息
- **公网IP**: {HOST}
- **操作系统**: {os_type}
- **部署时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}

### 软件版本
| 软件 | 版本 |
|------|------|
| PHP | {results.get('PHP', 'N/A')} |
| MySQL | {results.get('MySQL', 'N/A')} |
| Nginx | {results.get('Nginx', 'N/A')} |
| Python3 | {results.get('Python3', 'N/A')} |
| Git | {results.get('Git', 'N/A')} |

### 服务状态
| 服务 | 状态 |
|------|------|
| Nginx | {results.get('service_nginx', 'N/A')} |
| MySQL | {results.get('service_mysql', 'N/A')} |
| PHP-FPM | {results.get('service_php-fpm', results.get('service_php8.1-fpm', 'N/A'))} |
| SSH | {results.get('service_sshd', 'N/A')} |

### 安全配置
- **防火墙**: 仅开放 22(SSH), 80(HTTP), 443(HTTPS), 8080
- **SSH**: Root仅允许密钥登录, 最大尝试3次, 禁用X11转发, 空密码禁止
- **PHP**: expose_php=Off, display_errors=Off, log_errors=On

### 端口监听
```
{results.get('ports', 'N/A')}
```

### HTTP状态码: {results.get('http_status', 'N/A')}

### API测试
```
{results.get('api_courses', 'N/A')}
```

### 数据库
```
{results.get('db_tables', 'N/A')}
```

### 访问地址
- **前端首页**: http://{HOST}/
- **管理后台**: http://{HOST}/frontend/admin.html
- **API接口**: http://{HOST}/api/courses
- **Python开发服务器**: http://{HOST}:8080/frontend/index.html (需手动启动server.py)

### 项目目录
- **项目根目录**: {PROJECT_HOME}
- **日志目录**: {PROJECT_HOME}/logs
- **用户**: {PROJECT_USER}

### 数据库连接信息
- **数据库名**: team_match
- **用户名**: teammatch
- **密码**: Tm@2024#Secure
- **Root密码**: Root@Tm#2024#Admin (请及时修改)
"""
    print(report)

    # 保存报告
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deploy_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存至: {report_path}")


# ==================== 主流程 ====================

def main():
    print("="*60)
    print("  TeamMatch 远程服务器自动化部署")
    print(f"  目标服务器: {HOST}")
    print(f"  开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    deployer = RemoteDeployer(HOST, PORT, USER, PASSWORD)

    try:
        # 连接
        deployer.connect()

        # 步骤1: 探测环境
        os_type = step1_detect(deployer)
        print(f"\n检测到操作系统类型: {os_type}")

        # 步骤2: 安全加固
        try:
            step2_security(deployer, os_type)
        except Exception as e:
            print(f"[WARN] 安全加固部分失败: {e}")

        # 步骤3: 环境安装
        try:
            step3_environment(deployer, os_type)
        except Exception as e:
            print(f"[WARN] 环境安装部分失败: {e}")

        # 步骤4: 权限管理
        try:
            step4_permissions(deployer, os_type)
        except Exception as e:
            print(f"[WARN] 权限管理部分失败: {e}")

        # 步骤5: 部署代码
        try:
            step5_deploy(deployer)
        except Exception as e:
            print(f"[WARN] 代码部署部分失败: {e}")

        # 步骤6: 验证
        results = {}
        try:
            results = step6_verify(deployer)
        except Exception as e:
            print(f"[WARN] 验证测试部分失败: {e}")

        # 生成报告
        generate_report(results, os_type)

    except Exception as e:
        print(f"\n[FATAL] 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        deployer.close()

    print(f"\n{'='*60}")
    print(f"  部署结束: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
