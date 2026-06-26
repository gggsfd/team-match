#!/bin/bash
# Nginx config for TeamMatch - Route API to backend/index.php
cat > /etc/nginx/sites-available/teammatch << 'NGINXEOF'
server {
    listen 80 default_server;
    server_name 8.138.252.49 _;
    charset utf-8;

    # Frontend static files
    location / {
        root /opt/teammatch/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API - all requests go through backend/index.php (internal router)
    location /api/ {
        root /opt/teammatch;
        include fastcgi_params;
        fastcgi_pass unix:/run/php/php8.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME /opt/teammatch/backend/index.php;
        fastcgi_param PATH_INFO $uri;
    }

    # Security: deny hidden files
    location ~ /\. { deny all; }

    # Security: deny sensitive file types
    location ~ \.(sql|md|log)$ { deny all; }

    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;
}
NGINXEOF

echo "=== Nginx config ==="
head -25 /etc/nginx/sites-available/teammatch

echo ""
echo "=== Nginx test ==="
nginx -t && systemctl reload nginx && echo "NGINX_OK" || echo "NGINX_FAIL"

echo ""
echo "=== API test ==="
curl -s http://localhost/api/courses | head -20

echo ""
echo "=== Frontend test ==="
curl -s -o /dev/null -w "HTTP:%{http_code} Size:%{size_download}B\n" http://localhost/

echo ""
echo "=== Service status ==="
systemctl is-active nginx mysql php8.4-fpm
