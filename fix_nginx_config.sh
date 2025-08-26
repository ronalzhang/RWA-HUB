#!/bin/bash

# 修复nginx配置，将admin.lawsker.com正确代理到RWA-HUB应用

echo "🔧 修复nginx配置..."

SERVER_HOST="156.232.13.240"
SERVER_USER="root"
SERVER_PASS="Pr971V3j"

# 创建新的nginx配置
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
cat > /etc/nginx/sites-available/lawsker << 'EOF'
# Lawsker系统Nginx配置
# 主站配置 - lawsker.com
server {
    listen 80;
    server_name lawsker.com www.lawsker.com;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name lawsker.com www.lawsker.com;
    
    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/lawsker.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lawsker.com/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection \"1; mode=block\";
    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;
    
    # CORS头
    add_header Access-Control-Allow-Origin \"*\";
    add_header Access-Control-Allow-Methods \"GET, POST, PUT, DELETE, OPTIONS\";
    add_header Access-Control-Allow-Headers \"DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization\";
    
    # 前端代理 - 主站
    location / {
        proxy_pass http://127.0.0.1:6060;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}

# RWA-HUB管理后台配置 - admin.lawsker.com
server {
    listen 80;
    server_name admin.lawsker.com;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name admin.lawsker.com;
    
    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/lawsker.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lawsker.com/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection \"1; mode=block\";
    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;
    
    # CORS头
    add_header Access-Control-Allow-Origin \"*\";
    add_header Access-Control-Allow-Methods \"GET, POST, PUT, DELETE, OPTIONS\";
    add_header Access-Control-Allow-Headers \"DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization\";
    
    # RWA-HUB应用代理 - 代理到端口9000
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering off;
    }
}
EOF

# 测试nginx配置
nginx -t

if [ \$? -eq 0 ]; then
    echo '✅ Nginx配置语法正确'
    
    # 重新加载nginx
    systemctl reload nginx
    
    if [ \$? -eq 0 ]; then
        echo '✅ Nginx重新加载成功'
    else
        echo '❌ Nginx重新加载失败'
        exit 1
    fi
else
    echo '❌ Nginx配置语法错误'
    exit 1
fi
"

echo "✅ Nginx配置修复完成"
echo ""
echo "🔗 测试链接:"
echo "- RWA-HUB主页: https://admin.lawsker.com"
echo "- 资产详情: https://admin.lawsker.com/assets/RH-106046"