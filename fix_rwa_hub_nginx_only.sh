#!/bin/bash

# 只修复RWA-HUB的nginx配置，不影响其他应用

echo "🔧 只修复admin.lawsker.com的nginx配置..."

SERVER_HOST="156.232.13.240"
SERVER_USER="root"
SERVER_PASS="Pr971V3j"

# 备份原配置
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    cp /etc/nginx/sites-available/lawsker /etc/nginx/sites-available/lawsker.backup.$(date +%Y%m%d_%H%M%S)
    echo '✅ 已备份原nginx配置'
"

# 只修改admin.lawsker.com的代理配置
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    # 使用sed替换admin.lawsker.com的location /配置
    sed -i '/# 管理后台代理/,/location \/api\// {
        /location \/ {/,/}/ {
            s|proxy_pass http://127.0.0.1:6060/admin/;|proxy_pass http://127.0.0.1:9000;|
        }
    }' /etc/nginx/sites-available/lawsker
    
    echo '✅ 已修改admin.lawsker.com代理配置'
"

# 验证配置并重新加载
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    # 测试nginx配置
    nginx -t
    
    if [ \$? -eq 0 ]; then
        echo '✅ Nginx配置语法正确'
        
        # 重新加载nginx
        systemctl reload nginx
        
        if [ \$? -eq 0 ]; then
            echo '✅ Nginx重新加载成功'
            
            # 显示修改后的配置
            echo ''
            echo '📋 修改后的admin.lawsker.com配置:'
            grep -A 15 '# 管理后台代理' /etc/nginx/sites-available/lawsker
            
        else
            echo '❌ Nginx重新加载失败，恢复备份'
            cp /etc/nginx/sites-available/lawsker.backup.* /etc/nginx/sites-available/lawsker
            systemctl reload nginx
            exit 1
        fi
    else
        echo '❌ Nginx配置语法错误，恢复备份'
        cp /etc/nginx/sites-available/lawsker.backup.* /etc/nginx/sites-available/lawsker
        exit 1
    fi
"

echo ""
echo "✅ RWA-HUB nginx配置修复完成"
echo ""
echo "🔗 测试链接:"
echo "- RWA-HUB: https://admin.lawsker.com"
echo "- 资产详情: https://admin.lawsker.com/assets/RH-106046"
echo ""
echo "📝 修改内容:"
echo "- 只修改了admin.lawsker.com的代理目标"
echo "- 从 http://127.0.0.1:6060/admin/ 改为 http://127.0.0.1:9000"
echo "- 保持其他应用配置不变"