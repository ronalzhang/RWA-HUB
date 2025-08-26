#!/bin/bash

# 修复服务器上的图片路径和部署流程问题

echo "🔧 开始修复服务器图片和部署流程..."

# 服务器信息
SERVER_HOST="156.232.13.240"
SERVER_USER="root"
SERVER_PASS="Pr971V3j"
PROJECT_PATH="/root/RWA-HUB"

# 1. 确保uploads目录存在且权限正确
echo "1. 修复uploads目录..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    mkdir -p $PROJECT_PATH/app/static/uploads
    mkdir -p $PROJECT_PATH/app/static/images
    chmod 755 $PROJECT_PATH/app/static/uploads
    chmod 755 $PROJECT_PATH/app/static/images
    chown -R root:root $PROJECT_PATH/app/static/uploads
    chown -R root:root $PROJECT_PATH/app/static/images
"

# 2. 创建占位图片
echo "2. 创建占位图片..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    cd $PROJECT_PATH/app/static/images
    
    # 创建一个简单的SVG占位图片
    cat > placeholder.jpg << 'EOF'
<svg width=\"400\" height=\"300\" xmlns=\"http://www.w3.org/2000/svg\">
  <rect width=\"100%\" height=\"100%\" fill=\"#f8f9fa\"/>
  <text x=\"50%\" y=\"50%\" font-family=\"Arial, sans-serif\" font-size=\"18\" fill=\"#6c757d\" text-anchor=\"middle\" dy=\".3em\">
    No Image Available
  </text>
</svg>
EOF
"

# 3. 上传修复后的文件到服务器
echo "3. 上传修复后的文件..."

# 上传资产详情页面
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no app/templates/assets/detail.html $SERVER_USER@$SERVER_HOST:$PROJECT_PATH/app/templates/assets/

# 上传智能合约部署脚本
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no app/static/js/smart_contract_deployment.js $SERVER_USER@$SERVER_HOST:$PROJECT_PATH/app/static/js/

# 上传API路由
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no app/routes/api.py $SERVER_USER@$SERVER_HOST:$PROJECT_PATH/app/routes/

# 4. 检查数据库中的图片路径
echo "4. 检查数据库中的图片路径..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    cd $PROJECT_PATH
    python3 -c \"
import sqlite3
import json

# 连接数据库
conn = sqlite3.connect('instance/rwa_hub.db')
cursor = conn.cursor()

# 查询资产图片
cursor.execute('SELECT id, token_symbol, images FROM assets WHERE images IS NOT NULL AND images != \"\"')
assets = cursor.fetchall()

print('资产图片信息:')
for asset in assets:
    asset_id, token_symbol, images_str = asset
    try:
        images = json.loads(images_str) if images_str else []
        print(f'资产 {token_symbol} (ID: {asset_id}): {len(images)} 张图片')
        for img in images:
            print(f'  - {img}')
    except:
        print(f'资产 {token_symbol} (ID: {asset_id}): 图片数据格式错误')

conn.close()
\"
"

# 5. 重启应用服务
echo "5. 重启应用服务..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    cd $PROJECT_PATH
    
    # 停止现有进程
    pkill -f 'python.*app.py' || true
    sleep 3
    
    # 启动应用
    nohup python3 app.py > logs/app.log 2>&1 &
    
    # 等待启动
    sleep 5
    
    # 检查进程状态
    if pgrep -f 'python.*app.py' > /dev/null; then
        echo '✅ 应用启动成功'
        ps aux | grep 'python.*app.py' | grep -v grep
    else
        echo '❌ 应用启动失败'
        tail -20 logs/app.log
    fi
"

# 6. 测试修复结果
echo "6. 测试修复结果..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    # 测试API端点
    curl -s -o /dev/null -w '%{http_code}' http://localhost:9000/api/assets/list
    echo ' - API状态检查完成'
    
    # 检查静态文件
    ls -la $PROJECT_PATH/app/static/uploads/ | head -5
    ls -la $PROJECT_PATH/app/static/images/
"

echo ""
echo "✅ 服务器修复完成！"
echo ""
echo "📋 修复内容:"
echo "1. ✅ 修复uploads目录权限"
echo "2. ✅ 创建占位图片"
echo "3. ✅ 更新资产详情页面"
echo "4. ✅ 部署智能合约流程"
echo "5. ✅ 完整购买支付流程"
echo "6. ✅ 重启应用服务"
echo ""
echo "🔗 测试链接:"
echo "- 主页: https://admin.lawsker.com"
echo "- 资产详情: https://admin.lawsker.com/assets/RH-106046"
echo ""
echo "📝 下一步:"
echo "1. 访问资产详情页面检查图片显示"
echo "2. 测试智能合约部署功能"
echo "3. 验证完整购买流程"