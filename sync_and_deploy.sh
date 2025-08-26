#!/bin/bash

# RWA-HUB 标准化同步和部署脚本
# 确保GitHub仓库、本地和服务器代码三地同步

set -e  # 遇到错误立即退出

# 配置
SERVER_HOST="156.232.13.240"
SERVER_USER="root"
SERVER_PASS="Pr971V3j"
PROJECT_PATH="/root/RWA-HUB"
BACKUP_PATH="/root/RWA-HUB-backups"

echo "🚀 RWA-HUB 代码同步和部署"
echo "=================================="

# 1. 检查本地Git状态
echo "1️⃣ 检查本地Git状态..."
if [ -n "$(git status --porcelain)" ]; then
    echo "   📝 发现未提交的修改"
    git status --short
    
    read -p "   是否提交这些修改? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   💾 提交本地修改..."
        git add .
        
        # 获取提交消息
        echo "   请输入提交消息:"
        read -r commit_message
        
        git commit -m "$commit_message"
        echo "   ✅ 本地提交完成"
    else
        echo "   ⚠️  跳过提交，继续部署当前版本"
    fi
else
    echo "   ✅ 本地代码已是最新状态"
fi

# 2. 推送到GitHub
echo ""
echo "2️⃣ 推送到GitHub..."
git push origin main
if [ $? -eq 0 ]; then
    echo "   ✅ GitHub推送成功"
else
    echo "   ❌ GitHub推送失败"
    exit 1
fi

# 3. 获取当前提交哈希
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "   📍 当前提交: ${CURRENT_COMMIT:0:8}"

# 4. 服务器代码同步
echo ""
echo "3️⃣ 同步服务器代码..."

sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    echo '📂 进入项目目录...'
    cd $PROJECT_PATH
    
    echo '💾 创建备份...'
    mkdir -p $BACKUP_PATH
    BACKUP_NAME=\"rwa-hub-backup-\$(date +%Y%m%d_%H%M%S)\"
    cp -r . \$BACKUP_PATH/\$BACKUP_NAME
    echo \"   ✅ 备份创建: \$BACKUP_NAME\"
    
    echo '📥 拉取最新代码...'
    git fetch origin
    git reset --hard origin/main
    
    echo '🔍 检查代码版本...'
    SERVER_COMMIT=\$(git rev-parse HEAD)
    echo \"   📍 服务器提交: \${SERVER_COMMIT:0:8}\"
    
    if [ \"\$SERVER_COMMIT\" = \"$CURRENT_COMMIT\" ]; then
        echo '   ✅ 代码版本同步成功'
    else
        echo '   ⚠️  代码版本不匹配'
        exit 1
    fi
"

if [ $? -ne 0 ]; then
    echo "   ❌ 服务器代码同步失败"
    exit 1
fi

# 5. 重启应用服务
echo ""
echo "4️⃣ 重启应用服务..."

sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "
    cd $PROJECT_PATH
    
    echo '🛑 停止现有服务...'
    pkill -f 'python.*app.py' || true
    sleep 3
    
    echo '🧹 清理缓存...'
    find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name '*.pyc' -delete 2>/dev/null || true
    
    echo '🚀 启动应用...'
    nohup python app.py > logs/app.log 2>&1 &
    
    echo '⏳ 等待应用启动...'
    sleep 5
    
    echo '🔍 检查应用状态...'
    if pgrep -f 'python.*app.py' > /dev/null; then
        echo '   ✅ 应用启动成功'
        
        # 检查应用响应
        if curl -s -o /dev/null -w '%{http_code}' http://localhost:9000/ | grep -q '200'; then
            echo '   ✅ 应用响应正常'
        else
            echo '   ⚠️  应用响应异常，检查日志'
            tail -10 logs/app.log
        fi
    else
        echo '   ❌ 应用启动失败'
        tail -20 logs/app.log
        exit 1
    fi
"

if [ $? -ne 0 ]; then
    echo "   ❌ 应用重启失败"
    exit 1
fi

# 6. 验证部署
echo ""
echo "5️⃣ 验证部署结果..."

# 等待服务完全启动
sleep 3

# 测试主要端点
echo "   🔍 测试网站访问..."
if curl -k -s -o /dev/null -w '%{http_code}' https://rwa-hub.com/ | grep -q '200'; then
    echo "   ✅ 网站访问正常"
else
    echo "   ⚠️  网站访问异常"
fi

echo "   🔍 测试API端点..."
if curl -k -s -o /dev/null -w '%{http_code}' https://rwa-hub.com/api/assets/list | grep -q '200'; then
    echo "   ✅ API端点正常"
else
    echo "   ⚠️  API端点异常"
fi

# 7. 部署总结
echo ""
echo "=================================="
echo "🎉 部署完成!"
echo ""
echo "📊 部署信息:"
echo "   • 提交哈希: ${CURRENT_COMMIT:0:8}"
echo "   • 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "   • 服务器: $SERVER_HOST"
echo ""
echo "🔗 访问链接:"
echo "   • 主页: https://rwa-hub.com"
echo "   • 资产详情: https://rwa-hub.com/assets/RH-106046"
echo ""
echo "📝 后续操作:"
echo "   • 检查应用日志: ssh root@$SERVER_HOST 'tail -f $PROJECT_PATH/logs/app.log'"
echo "   • 查看进程状态: ssh root@$SERVER_HOST 'ps aux | grep python'"
echo "   • 回滚到备份: ssh root@$SERVER_HOST 'ls -la $BACKUP_PATH/'"