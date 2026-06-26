#!/bin/bash
echo "=== 1. Backend index.php exists? ==="
ls -la /opt/teammatch/backend/index.php

echo ""
echo "=== 2. Nginx error log ==="
tail -20 /var/log/nginx/error.log

echo ""
echo "=== 3. Test backend index.php directly via CLI ==="
php /opt/teammatch/backend/index.php 2>&1 || echo "CLI_TEST_FAILED"

echo ""
echo "=== 4. Test PHP-FPM with a minimal script ==="
echo '<?php echo "PHP_WORKS";' > /opt/teammatch/backend/test_php.php
curl -s http://localhost/backend/test_php.php 2>&1
rm -f /opt/teammatch/backend/test_php.php

echo ""
echo "=== 5. Check PHP-FPM pool config ==="
grep -E "^listen|^security|^user|^group" /etc/php/8.4/fpm/pool.d/www.conf 2>/dev/null

echo ""
echo "=== 6. Check PHP-FPM status ==="
systemctl status php8.4-fpm 2>&1 | head -10

echo ""
echo "=== 7. Try curl with verbose ==="
curl -v http://localhost/api/courses 2>&1 | head -30

echo ""
echo "=== 8. Check if auth header causes issues ==="
cd /opt/teammatch/backend
php -r "
\$_SERVER['REQUEST_URI'] = '/api/courses';
\$_SERVER['REQUEST_METHOD'] = 'GET';
require 'index.php';
" 2>&1
