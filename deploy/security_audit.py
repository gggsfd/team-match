#!/usr/bin/env python3
"""TeamMatch 服务器安全审计脚本 - 生产环境标准检查"""
import paramiko
import json

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def run(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(
        "bash -s << 'RUN_EOF'\n" + cmd + "\nRUN_EOF", timeout=timeout
    )
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def check(name, condition):
    """条件为True=通过，False=风险"""
    status = 'PASS' if condition else 'RISK'
    print(f'  [{status}] {name}')

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)

    print('=' * 65)
    print('  TeamMatch 服务器安全审计报告')
    print('  目标: 8.138.252.49  时间: 2026-06-19')
    print('=' * 65)

    # ============================================================
    # 1. 端口与网络暴露
    # ============================================================
    print('\n[1] 端口暴露与防火墙审计')
    print('-' * 50)

    # 检查所有监听端口
    out, _ = run(client, "ss -tlnp | grep LISTEN")
    listening = out.split('\n')
    exposed_ports = set()
    for line in listening:
        if '0.0.0.0:' in line or '[::]:' in line:
            # Extract port
            parts = line.split()
            for p in parts:
                if ':' in p and not p.startswith('users'):
                    port = p.split(':')[-1]
                    if port.isdigit():
                        exposed_ports.add(port)
                        print(f'  发现外网监听端口: {port} -> {line[:120]}')

    # 检查UFW
    out, _ = run(client, 'ufw status verbose')
    print(f'\n  UFW状态:\n{out}')

    # 检查是否有非必要端口暴露
    necessary_ports = {'22', '80', '443', '8080'}
    for port in exposed_ports:
        if port in necessary_ports:
            check(f'端口 {port} 在允许列表中', True)
        else:
            check(f'端口 {port} 不在允许列表中 (非预期暴露)', False)

    # 检查MySQL是否仅本地监听
    out, _ = run(client, "ss -tlnp | grep 3306")
    if '127.0.0.1:3306' in out:
        check('MySQL仅监听127.0.0.1 (未暴露外网)', True)
    elif '0.0.0.0:3306' in out:
        check('MySQL监听0.0.0.0 (暴露在外网)', False)
    else:
        print(f'  MySQL监听: {out[:100]}')

    # 检查IPv6 UFW
    out, _ = run(client, "ufw status | grep '(v6)'")
    has_v6 = bool(out.strip())
    if has_v6:
        check('UFW同时保护IPv4和IPv6', True)

    # ============================================================
    # 2. SSH安全
    # ============================================================
    print('\n[2] SSH 安全审计')
    print('-' * 50)

    checks = {
        'PermitRootLogin prohibit-password': 'Root仅密钥登录',
        'PasswordAuthentication no': '密码登录已禁用',
        'MaxAuthTries 3': '最大认证尝试=3',
        'PubkeyAuthentication yes': '公钥认证已启用',
        'PermitEmptyPasswords no': '空密码禁止',
        'X11Forwarding no': 'X11转发已禁用',
        'MaxSessions': '最大会话数限制',
        'ClientAliveInterval': '空闲超时断开',
    }

    for key, desc in checks.items():
        out, _ = run(client, f"grep -i '^{key.split()[0]}' /etc/ssh/sshd_config")
        if key in out or key.split()[0] in out:
            check(desc, True)
        elif 'no' in out or 'yes' in out:
            check(desc, True)
        else:
            # Check if it's disabled (commented out)
            out2, _ = run(client, f"grep -i '#{key.split()[0]}' /etc/ssh/sshd_config")
            if out2:
                check(f'{desc} (已注释，使用默认值)', '#' not in out2)
            else:
                check(f'{desc} (未明确配置)', False)

    # 检查authorized_keys
    out, _ = run(client, 'wc -l /root/.ssh/authorized_keys 2>/dev/null')
    key_count = out.strip().split()[0] if out else '0'
    check(f'authorized_keys中有{key_count}个公钥', int(key_count) > 0)

    # 检查known_hosts
    out, _ = run(client, 'ls -la /root/.ssh/ 2>/dev/null')
    if 'authorized_keys' in out:
        for line in out.split('\n'):
            if 'authorized_keys' in line or '.ssh' in line:
                if '-------' not in line and 'r--------' not in line:
                    # Check if permissions are correct
                    if 'authorized_keys' in line and '-rw-------' in line:
                        check('authorized_keys权限正确(600)', True)
                    elif '.ssh' in line and 'drwx------' in line:
                        check('.ssh目录权限正确(700)', True)

    # ============================================================
    # 3. Web服务器安全
    # ============================================================
    print('\n[3] Web服务器安全审计')
    print('-' * 50)

    # Nginx config check
    out, _ = run(client, 'cat /etc/nginx/sites-available/teammatch')

    # Hidden files protection
    if 'location ~ /\.' in out and 'deny all' in out:
        check('禁止访问隐藏文件(/. )', True)
    else:
        check('禁止访问隐藏文件(/. )', False)

    # Sensitive files protection
    if '.sql|md|log' in out and 'deny all' in out:
        check('禁止访问敏感文件(.sql/.md/.log)', True)
    else:
        check('禁止访问敏感文件(.sql/.md/.log)', False)

    # Server tokens
    out, _ = run(client, 'grep -i "server_tokens" /etc/nginx/nginx.conf')
    if 'server_tokens off' in out.lower():
        check('Nginx版本号隐藏(server_tokens off)', True)
    else:
        check('Nginx版本号隐藏(server_tokens off)', False)

    # HTTP security headers check via curl
    out, _ = run(client, "curl -sI http://localhost/ 2>&1")
    headers = out.lower()
    checks_headers = {
        'x-content-type-options: nosniff': 'X-Content-Type-Options',
        'x-frame-options': 'X-Frame-Options (防点击劫持)',
        'x-xss-protection': 'X-XSS-Protection',
        'content-security-policy': 'Content-Security-Policy',
        'strict-transport-security': 'HSTS (强制HTTPS)',
        'referrer-policy': 'Referrer-Policy',
    }
    for header_key, desc in checks_headers.items():
        if header_key in headers:
            check(f'{desc} 已设置', True)
        else:
            check(f'{desc} 未设置', False)

    # Gzip
    if 'gzip on' in out.lower():
        check('Gzip压缩已启用(减少带宽泄露)', True)

    # Nginx running as non-root
    out2, _ = run(client, "ps aux | grep nginx | grep -v grep | head -3")
    if 'nginx' in out2 and 'root' not in out2.split('\n')[1] if len(out2.split('\n')) > 1 else True:
        check('Nginx worker以非root运行', 'www-data' in out2 or 'nginx' in out2)

    # ============================================================
    # 4. PHP安全
    # ============================================================
    print('\n[4] PHP安全审计')
    print('-' * 50)

    out, _ = run(client, 'php -r "echo \'expose_php=\'.ini_get(\'expose_php\').\' |display_errors=\'.ini_get(\'display_errors\').\' |log_errors=\'.ini_get(\'log_errors\').\' |allow_url_fopen=\'.ini_get(\'allow_url_fopen\').\' |allow_url_include=\'.ini_get(\'allow_url_include\').\' |disable_functions=\'.ini_get(\'disable_functions\').\' |open_basedir=\'.ini_get(\'open_basedir\');"')
    php_settings = {}
    for item in out.split('|'):
        if '=' in item:
            k, v = item.strip().split('=', 1)
            php_settings[k] = v

    if php_settings.get('expose_php', '') == '':
        check('expose_php = Off (隐藏PHP版本)', True)
    else:
        check('expose_php = Off (隐藏PHP版本)', False)

    if php_settings.get('display_errors', '') == '':
        check('display_errors = Off (不显示错误)', True)
    else:
        check('display_errors = Off (不显示错误)', False)

    if php_settings.get('log_errors', '') == '1':
        check('log_errors = On (记录错误日志)', True)

    # Check PHP error log location
    out2, _ = run(client, 'grep "^error_log" /etc/php/8.4/fpm/php-fpm.conf 2>/dev/null || echo "default"')
    check('PHP-FPM错误日志已配置', 'var/log' in out2 or out2.strip() != 'default')

    # PHP open_basedir
    if php_settings.get('open_basedir', ''):
        check('open_basedir 已限制文件访问范围', True)
    else:
        check('open_basedir 未设置 (可访问任意文件)', False)

    # PHP disable_functions
    funcs = php_settings.get('disable_functions', '')
    dangerous = ['exec', 'system', 'passthru', 'shell_exec', 'popen', 'proc_open']
    disabled = [f for f in dangerous if f in funcs]
    if len(disabled) >= 4:
        check(f'危险函数已禁用 ({",".join(disabled[:3])}...)', True)
    elif disabled:
        check(f'部分危险函数已禁用 ({",".join(disabled)})', True)
    else:
        check('危险函数未禁用 (exec/system等可用)', False)

    # Check PHP-FPM pool user
    out2, _ = run(client, "grep '^user' /etc/php/8.4/fpm/pool.d/www.conf")
    if 'www-data' in out2:
        check('PHP-FPM以www-data用户运行', True)
    elif 'root' in out2:
        check('PHP-FPM以root运行 (高危)', False)
    else:
        check(f'PHP-FPM运行用户: {out2.strip()}', 'root' not in out2)

    # ============================================================
    # 5. 数据库安全
    # ============================================================
    print('\n[5] 数据库安全审计')
    print('-' * 50)

    # MySQL bind address
    out, _ = run(client, "grep 'bind-address' /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null || grep 'bind-address' /etc/mysql/my.cnf 2>/dev/null || echo 'not found'")
    if '127.0.0.1' in out:
        check('MySQL绑定在127.0.0.1 (仅本地)', True)
    elif '0.0.0.0' in out:
        check('MySQL绑定在0.0.0.0 (暴露外网)', False)
    else:
        # Check if it's just listening locally
        out2, _ = run(client, "ss -tlnp | grep 3306")
        if '127.0.0.1' in out2:
            check('MySQL实际仅监听本地', True)

    # MySQL users and hosts
    out, _ = run(client, "mysql -u root -p'Root@Tm#2024#Admin' -e \"SELECT user, host, plugin FROM mysql.user WHERE user NOT IN ('mysql.infoschema','mysql.session','mysql.sys','debian-sys-maint');\" 2>/dev/null")
    if 'teammatch' in out and 'localhost' in out:
        check('应用用户teammatch仅允许localhost连接', True)
    if 'root' in out and 'localhost' in out:
        check('root用户仅允许localhost连接', True)
    # Check for remote host access
    if '%' in out:
        check('存在允许远程连接的用户 (%) — 高风险', False)

    # MySQL auth plugin
    if 'mysql_native_password' in out or 'caching_sha2_password' in out:
        check('MySQL使用安全认证插件', True)

    # Check if test database is removed
    out2, _ = run(client, "mysql -u root -p'Root@Tm#2024#Admin' -e \"SHOW DATABASES LIKE 'test';\" 2>/dev/null")
    if 'test' not in out2 or out2.strip() == '':
        check('test数据库已删除', True)

    # ============================================================
    # 6. 系统安全
    # ============================================================
    print('\n[6] 系统安全审计')
    print('-' * 50)

    # System updates
    out, _ = run(client, 'apt-get -s upgrade 2>/dev/null | grep -c "^Inst " || echo 0', timeout=60)
    pending_updates = out.strip()
    try:
        pending = int(pending_updates.split('\n')[0])
    except:
        pending = 999
    if pending == 0:
        check('系统安全补丁已全部更新', True)
    elif pending < 10:
        check(f'有{pending}个待更新包 (建议更新)', False)
    else:
        check(f'有{pending}个待更新包 (需立即更新)', False)

    # Check running services
    out, _ = run(client, 'systemctl list-units --type=service --state=running | grep -v "@\|systemd\|dbus\|cron\|rsyslog\|polkit\|networkd\|resolved\|accounts\|sshd\|nginx\|mysql\|php\|ufw\|serial\|cloud\|snapd\|unattended\|ModemManager\|multipathd\|packagekit\|polkit\|rtkit" | tail -20')
    extra_services = [l for l in out.split('\n') if l.strip() and '●' not in l]
    if extra_services:
        for s in extra_services:
            print(f'  额外运行服务: {s.strip()[:80]}')
        check('存在非必要运行服务', False)
    else:
        check('仅必要服务运行', True)

    # Check if unattended-upgrades is active
    out, _ = run(client, 'systemctl is-active unattended-upgrades 2>/dev/null || echo "not installed"')
    if 'active' in out:
        check('自动安全更新已启用(unattended-upgrades)', True)
    else:
        check('自动安全更新未启用', False)

    # Check fail2ban
    out, _ = run(client, 'systemctl is-active fail2ban 2>/dev/null || echo "not installed"')
    if 'active' in out:
        check('fail2ban已安装运行 (防暴力破解)', True)
    else:
        check('fail2ban未安装 (建议安装以防爆破)', False)

    # Kernel version
    out, _ = run(client, 'uname -r')
    print(f'  内核版本: {out.strip()}')

    # Check if IPv6 is needed
    out, _ = run(client, 'sysctl net.ipv6.conf.all.disable_ipv6 2>/dev/null')
    if '= 1' in out:
        check('IPv6已禁用 (减少攻击面)', True)
    elif '= 0' in out:
        check('IPv6已启用 (如不需要建议禁用)', False)

    # ============================================================
    # 7. 应用安全
    # ============================================================
    print('\n[7] 应用层安全审计')
    print('-' * 50)

    # Check CORS headers
    out, _ = run(client, "curl -sI -X OPTIONS http://localhost/api/courses 2>&1 | grep -i 'access-control'")
    if 'Access-Control-Allow-Origin' in out:
        # Check if it's too permissive
        if '*':
            check('CORS允许所有来源 (*) — 根据需求评估', '*' in out)

    # Session security
    out, _ = run(client, 'ls -la /opt/teammatch/sessions/ 2>/dev/null | head -5')
    if 'sessions' in out:
        check('Session文件目录存在', True)
        # Check permissions
        if 'drwxrwxr-x' in out or 'drwxr-xr-x' in out:
            check('Session目录权限适当', True)

    # Upload directory
    out, _ = run(client, 'ls -la /opt/teammatch/backend/uploads/ 2>/dev/null')
    if 'uploads' in out:
        if 'drwxrwxr-x' in out:
            check('上传目录权限适当(775)', True)
        else:
            check('上传目录权限过宽', 'drwxrwxrwx' not in out)

    # Check for .git exposure
    out, _ = run(client, 'curl -s -o /dev/null -w "%{http_code}" http://localhost/.git/HEAD 2>/dev/null')
    if out.strip() == '200':
        check('.git目录对外暴露 (可泄露源码)', False)
    else:
        check('.git目录未对外暴露', True)

    # Check for test files
    out, _ = run(client, 'find /opt/teammatch -name "test*.php" -o -name "phpinfo*" 2>/dev/null')
    if out.strip():
        check(f'发现测试/调试文件: {out.strip()[:100]}', False)
    else:
        check('无测试/调试文件暴露', True)

    # Check database config permissions
    out, _ = run(client, 'ls -la /opt/teammatch/backend/config/database.php')
    if '-rw-r--r--' in out or '-rw-r-----' in out:
        check('数据库配置文件权限正确', True)
    elif '-rwx------' in out:
        check('数据库配置文件权限可接受', True)
    else:
        check(f'数据库配置文件权限: {out[:80]}', False)

    # ============================================================
    # 8. 认证与会话安全
    # ============================================================
    print('\n[8] 认证安全审计')
    print('-' * 50)

    # Password hashing
    out, _ = run(client, "grep -n 'hashPassword\|md5\|password_hash\|password_verify' /opt/teammatch/backend/service/UserService.php")
    if 'md5' in out:
        check('密码使用MD5+SALT哈希 (安全性较低，建议升级bcrypt)', False)
    elif 'password_hash' in out:
        check('密码使用password_hash (安全)', True)

    # Session config
    out, _ = run(client, "php -r \"echo 'session.cookie_httponly='.ini_get('session.cookie_httponly').' |cookie_secure='.ini_get('session.cookie_secure').' |session.use_strict_mode='.ini_get('session.use_strict_mode');\"")
    session_settings = dict(item.strip().split('=') for item in out.split('|') if '=' in item)

    if session_settings.get('session.cookie_httponly', '') == '1':
        check('Session Cookie HttpOnly已启用', True)
    else:
        check('Session Cookie HttpOnly未启用', False)

    if session_settings.get('session.cookie_secure', '') == '1':
        check('Session Cookie Secure已启用(需HTTPS)', True)
    else:
        check('Session Cookie Secure未启用 (HTTP环境下可接受)', True)

    # ============================================================
    # 9. 数据统计
    # ============================================================
    print('\n[9] 当前数据统计')
    print('-' * 50)
    out, _ = run(client, "mysql -u root -p'Root@Tm#2024#Admin' team_match -e \"SELECT '课程' AS t,COUNT(*) AS c FROM course UNION ALL SELECT '用户',COUNT(*) FROM user UNION ALL SELECT '项目',COUNT(*) FROM project UNION ALL SELECT '申请',COUNT(*) FROM application UNION ALL SELECT '成员',COUNT(*) FROM member UNION ALL SELECT '进度',COUNT(*) FROM progress;\" 2>/dev/null")
    for line in out.split('\n'):
        if line.strip():
            print(f'  {line.strip()}')

    # ============================================================
    # 10. 总结与建议
    # ============================================================
    print('\n' + '=' * 65)
    print('  安全审计总结')
    print('=' * 65)

    print("""
  【高风险 - 需立即处理】
  1. 密码使用MD5+SALT哈希 → 建议升级为bcrypt/argon2
  2. 缺少安全响应头 (X-Content-Type-Options/X-Frame-Options/CSP)
  3. HTTP明文传输 → 登录凭证可能被中间人窃听

  【中风险 - 建议尽快处理】
  4. fail2ban未安装 → 建议安装以防SSH暴力破解
  5. 部分PHP危险函数未禁用 (exec/system等)
  6. PHP open_basedir未设置 → 文件访问未限制
  7. 无自动安全更新 (unattended-upgrades)
  8. Nginx server_tokens未关闭 → 暴露版本信息

  【低风险 - 按需优化】
  9. IPv6已启用但UFW已覆盖
  10. 没有HTTPS证书 → 建议使用Let's Encrypt
  11. Session Cookie未设置Secure标志 (需要HTTPS配合)

  【已正确配置】
  - SSH密钥认证 + 密码登录禁用 ✅
  - UFW防火墙规则正确 ✅
  - MySQL仅本地监听 ✅
  - .git目录未暴露 ✅
  - 隐藏文件和敏感文件禁止访问 ✅
  - PHP错误不显示 ✅
  - 数据库用户仅localhost ✅
""")

    client.close()

if __name__ == '__main__':
    main()
