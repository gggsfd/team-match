#!/usr/bin/env python3
"""Fix PHP security settings that sed missed"""
import paramiko

HOST = '8.138.252.49'
KEY_FILE = 'C:/Users/123/.ssh/teammatch_local'

def run(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(
        "bash -s << 'RUN_EOF'\n" + cmd + "\nRUN_EOF", timeout=timeout
    )
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, 'root', pkey=key, timeout=15)

    # Check which PHP ini files exist
    print('=== PHP INI files ===')
    out, _ = run(client, 'find /etc/php -name "php.ini" 2>/dev/null')
    print(out)

    # Check current settings
    print('\n=== Current PHP FPM settings ===')
    out, _ = run(client, 'grep -E "^(session.cookie_httponly|session.use_strict_mode|session.cookie_samesite|disable_functions|open_basedir|allow_url_fopen|allow_url_include)" /etc/php/8.4/fpm/php.ini')
    print(out if out else '(none matched)')

    # Check what the lines look like
    print('\n=== Raw lines in FPM ini ===')
    out, _ = run(client, 'grep -n "cookie_httponly\\|use_strict_mode\\|cookie_samesite\\|disable_functions\\|open_basedir\\|allow_url_fopen\\|allow_url_include" /etc/php/8.4/fpm/php.ini | head -10')
    print(out if out else '(none found)')

    # Use python3 for reliable ini editing
    print('\n=== Fixing PHP FPM settings with Python ===')
    out, _ = run(client, """
python3 << 'PYFIX'
import re

ini_file = '/etc/php/8.4/fpm/php.ini'
with open(ini_file, 'r') as f:
    content = f.read()

# Define the settings to apply
settings = {
    r'^;?session\\.cookie_httponly\\s*=': 'session.cookie_httponly = 1',
    r'^;?session\\.use_strict_mode\\s*=': 'session.use_strict_mode = 1',
    r'^;?session\\.cookie_samesite\\s*=': 'session.cookie_samesite = "Lax"',
    r'^;?allow_url_fopen\\s*=': 'allow_url_fopen = Off',
    r'^;?allow_url_include\\s*=': 'allow_url_include = Off',
    r'^;?disable_functions\\s*=': 'disable_functions = exec,system,passthru,shell_exec,popen,proc_open,pcntl_exec,putenv',
    r'^;?open_basedir\\s*=': 'open_basedir = /opt/teammatch/:/tmp/:/usr/share/php/',
}

for pattern, replacement in settings.items():
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        print(f'  Updated: {replacement}')
    else:
        # Add if not found
        content += f'\\n{replacement}\\n'
        print(f'  Added: {replacement}')

with open(ini_file, 'w') as f:
    f.write(content)

print('Done')
PYFIX

# Also apply to CLI ini for consistency
cp /etc/php/8.4/fpm/php.ini /etc/php/8.4/cli/php.ini.backup 2>/dev/null
# Copy relevant settings to CLI too
for setting in "session.cookie_httponly = 1" "session.use_strict_mode = 1" "session.cookie_samesite = \\\"Lax\\\"" "disable_functions = exec,system,passthru,shell_exec,popen,proc_open,pcntl_exec,putenv"; do
    grep -q "$setting" /etc/php/8.4/cli/php.ini 2>/dev/null || echo "$setting" >> /etc/php/8.4/cli/php.ini
done

systemctl restart php8.4-fpm
echo "PHP-FPM Restarted"
""", timeout=30)
    print(out)
    if err:
        print(f'ERR: {err[:300]}')

    # Verify FPM settings via a web request
    print('\n=== Verify via FPM (web request) ===')
    # Create a test PHP file
    out, _ = run(client, """
cat > /opt/teammatch/backend/_sec_check.php << 'PHPEOF'
<?php
header('Content-Type: text/plain');
echo 'httponly=' . ini_get('session.cookie_httponly') . "\\n";
echo 'strict=' . ini_get('session.use_strict_mode') . "\\n";
echo 'samesite=' . ini_get('session.cookie_samesite') . "\\n";
echo 'open_basedir=' . ini_get('open_basedir') . "\\n";
echo 'disable_functions_len=' . strlen(ini_get('disable_functions')) . "\\n";
echo 'url_fopen=' . ini_get('allow_url_fopen') . "\\n";
echo 'url_include=' . ini_get('allow_url_include') . "\\n";
PHPEOF

chown teammatch:teammatch /opt/teammatch/backend/_sec_check.php
curl -s http://localhost/backend/_sec_check.php
rm -f /opt/teammatch/backend/_sec_check.php
""")
    print(out)

    # Final API test
    print('\n=== API still working? ===')
    out, _ = run(client, "curl -s http://localhost/api/courses | head -50")
    print(out[:150] if out else '(empty)')

    client.close()

if __name__ == '__main__':
    main()
