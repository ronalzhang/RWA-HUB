#!/bin/bash

# 智能合约部署脚本修复部署脚本
echo "🚀 开始部署智能合约脚本修复..."

# 服务器配置
SERVER_HOST="156.236.74.200"
SERVER_USER="root"
SERVER_PASS="Pr971V3j"
PROJECT_PATH="/root/RWA-HUB"

echo "📁 上传修复后的模板文件..."

# 上传资产详情页面模板
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    app/templates/assets/detail.html \
    $SERVER_USER@$SERVER_HOST:$PROJECT_PATH/app/templates/assets/

if [ $? -eq 0 ]; then
    echo "✅ 资产详情页面模板上传成功"
else
    echo "❌ 资产详情页面模板上传失败"
    exit 1
fi

# 上传资产创建页面模板
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    app/templates/assets/create.html \
    $SERVER_USER@$SERVER_HOST:$PROJECT_PATH/app/templates/assets/

if [ $? -eq 0 ]; then
    echo "✅ 资产创建页面模板上传成功"
else
    echo "❌ 资产创建页面模板上传失败"
    exit 1
fi

# 确保智能合约部署脚本是最新的
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
    app/static/js/smart_contract_deployment.js \
    $SERVER_USER@$SERVER_HOST:$PROJECT_PATH/app/static/js/

if [ $? -eq 0 ]; then
    echo "✅ 智能合约部署脚本上传成功"
else
    echo "❌ 智能合约部署脚本上传失败"
    exit 1
fi

echo "🔄 重启服务器应用..."

# 重启应用
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST << 'EOF'
cd /root/RWA-HUB

# 停止现有进程
pkill -f "python.*app.py" || true
pkill -f "gunicorn" || true

# 等待进程完全停止
sleep 3

# 启动应用
nohup python app.py > app.log 2>&1 &

# 等待应用启动
sleep 5

# 检查应用是否启动成功
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✅ 应用重启成功"
else
    echo "❌ 应用重启失败"
    exit 1
fi
EOF

if [ $? -eq 0 ]; then
    echo "✅ 服务器应用重启成功"
else
    echo "❌ 服务器应用重启失败"
    exit 1
fi

echo "🎉 智能合约部署脚本修复完成！"
echo ""
echo "📝 修复内容："
echo "- ✅ 修复了资产详情页面的智能合约部署脚本引用"
echo "- ✅ 修复了资产创建页面的智能合约部署脚本引用"
echo "- ✅ 确保了智能合约部署脚本文件是最新版本"
echo "- ✅ 重启了服务器应用"
echo ""
echo "🔗 测试链接："
echo "1. 资产详情页面: https://rwa-hub.com/assets/RH-106046"
echo "2. 资产创建页面: https://rwa-hub.com/assets/create"
echo ""
echo "✨ deploySmartContract函数现在应该可以正常工作了！"
