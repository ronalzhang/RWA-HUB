#!/bin/bash

# RWA-HUB 全自动部署脚本
# 自动提交代码、拉取更新、重启PM2应用

set -e

# 配置文件路径
CONFIG_FILE="deploy.config"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件 $CONFIG_FILE 不存在"
    echo "📝 正在创建配置文件模板..."
    
    cat > "$CONFIG_FILE" << 'EOF'
# RWA-HUB 部署配置文件
# 请根据实际情况修改以下配置

# 服务器配置
SERVER_HOST="156.232.13.240"
SERVER_USER="root"
SERVER_PASSWORD="Pr971V3j"
SERVER_PATH="/root/RWA-HUB"

# GitHub仓库配置
GITHUB_BRANCH="main"

# PM2应用配置
PM2_APP_NAME="rwa-hub"
APP_PORT="9000"
EOF
    
    echo "✅ 配置文件已创建: $CONFIG_FILE"
    echo "⚠️  请编辑配置文件并填入正确的服务器信息，然后重新运行部署脚本"
    exit 1
fi

# 加载配置文件
echo "📋 加载配置文件..."
source "$CONFIG_FILE"
# 积极清理所有配置变量中的空白字符
SERVER_HOST=$(echo "$SERVER_HOST" | tr -d '[:space:]')
SERVER_USER=$(echo "$SERVER_USER" | tr -d '[:space:]')
SERVER_PASSWORD=$(echo "$SERVER_PASSWORD" | tr -d '[:space:]')
SERVER_PATH=$(echo "$SERVER_PATH" | tr -d '[:space:]')
GITHUB_BRANCH=$(echo "$GITHUB_BRANCH" | tr -d '[:space:]')
PM2_APP_NAME=$(echo "$PM2_APP_NAME" | tr -d '[:space:]')
APP_PORT=$(echo "$APP_PORT" | tr -d '[:space:]')


# 验证必要配置
required_vars=("SERVER_HOST" "SERVER_USER" "SERVER_PASSWORD" "SERVER_PATH" "PM2_APP_NAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 配置项 $var 未设置，请检查配置文件"
        exit 1
    fi
done

echo "✅ 配置加载完成"

# 检查必要工具
echo "🔍 检查必要工具..."
if ! command -v sshpass &> /dev/null; then
    echo "❌ sshpass 未安装，请先安装："
    echo "   macOS: brew install sshpass"
    echo "   Ubuntu: sudo apt-get install sshpass"
    echo "   CentOS: sudo yum install sshpass"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ git 未安装，请先安装git"
    exit 1
fi

echo "✅ 工具检查完成"

# 提交代码到GitHub
echo "📤 提交代码到GitHub仓库..."

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 发现未提交的更改，正在提交..."
    
    # 添加所有更改（排除敏感文件）
    git add .
    git reset HEAD deploy.config 2>/dev/null || true  # 确保配置文件不被提交
    
    # 提交更改
    COMMIT_MESSAGE="自动部署更新 - $(date '+%Y-%m-%d %H:%M:%S')"
    git commit -m "$COMMIT_MESSAGE"
    
    echo "✅ 代码已提交: $COMMIT_MESSAGE"
else
    echo "✅ 代码已是最新状态"
fi

# 推送到远程仓库
echo "🔄 推送到远程仓库..."
git push origin "$GITHUB_BRANCH" || {
    echo "❌ 推送失败，请检查GitHub仓库配置"
    exit 1
}

echo "✅ 代码已推送到GitHub"

# 显示部署信息（无需确认，自动继续）
echo ""
echo "🚀 开始自动部署..."
echo "   服务器: $SERVER_HOST"
echo "   应用: $PM2_APP_NAME"
echo "   路径: $SERVER_PATH"
echo "   端口: $APP_PORT"
echo ""

# 连接服务器并执行部署
echo "🔗 连接服务器并执行部署..."


REMOTE_SCRIPT="
set -e
echo '🔧 在服务器上执行部署...'
cd \$SERVER_PATH
echo '📥 拉取最新代码...'
git pull origin \$GITHUB_BRANCH
if ! command -v pm2 &> /dev/null; then
    echo '❌ PM2未安装，请先安装PM2'
    exit 1
fi
echo '🔄 重启PM2应用: \$PM2_APP_NAME'
if pm2 list | grep -q '\$PM2_APP_NAME'; then
    pm2 restart \$PM2_APP_NAME
    echo '✅ PM2应用 \$PM2_APP_NAME 重启成功'
else
    echo '❌ PM2应用 \$PM2_APP_NAME 不存在'
    echo '📋 当前PM2应用列表:'
    pm2 list
    exit 1
fi
echo '💾 保存PM2配置...'
pm2 save
echo '⏳ 等待应用启动...'
sleep 3
echo '🔍 检查应用状态...'
if pm2 list | grep -q '\$PM2_APP_NAME.*online'; then
    echo '✅ 应用运行正常'
    echo '🧪 测试API连接...'
    if curl -s --max-time 10 http://localhost:\$APP_PORT/api/health/ > /dev/null; then
        echo '✅ API连接正常'
    else
        echo '⚠️  API连接测试超时，但应用已启动'
    fi
    echo '📊 应用状态:'
    pm2 list | grep '\$PM2_APP_NAME' || true
else
    echo '❌ 应用启动失败'
    echo '📋 PM2状态:'
    pm2 list
    echo '📝 最近日志:'
    pm2 logs \$PM2_APP_NAME --lines 10 --nostream || true
    exit 1
fi
echo '🎉 部署完成！'
"

sshpass -p "\$SERVER_PASSWORD" ssh -T -o StrictHostKeyChecking=no "\$SERVER_USER@\$SERVER_HOST" "\$REMOTE_SCRIPT"



# 检查部署结果
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 自动部署成功完成！"
    echo ""
    echo "📊 部署摘要:"
    echo "  - 服务器地址: http://$SERVER_HOST:$APP_PORT"
    echo "  - 管理后台: http://$SERVER_HOST:$APP_PORT/admin"
    echo "  - PM2应用: $PM2_APP_NAME"
    echo ""
    echo "🔍 验证部署:"
    echo "  curl -s http://$SERVER_HOST:$APP_PORT/api/health/"
    echo ""
    echo "📝 常用命令:"
    echo "  查看日志: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'pm2 logs $PM2_APP_NAME'"
    echo "  查看状态: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'pm2 status'"
    echo "  重启应用: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'pm2 restart $PM2_APP_NAME'"
else
    echo ""
    echo "❌ 部署失败！请检查服务器日志"
    echo "🔍 查看错误日志:"
    echo "  sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'pm2 logs $PM2_APP_NAME --err'"
    exit 1
fi