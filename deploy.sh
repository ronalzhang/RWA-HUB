#!/bin/bash

# RWA-HUB 简化部署脚本
# 只提交代码、拉取更新、重启应用

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
SERVER_HOST="156.236.74.200"
SERVER_USER="root"
SERVER_PASSWORD="Pr971V3j"
SERVER_PATH="/root/RWA-HUB"

# GitHub仓库配置
GITHUB_BRANCH="main"

# 应用配置
APP_PORT="9000"
EOF
    
    echo "✅ 配置文件已创建: $CONFIG_FILE"
    echo "⚠️  请编辑配置文件并填入正确的服务器信息，然后重新运行部署脚本"
    exit 1
fi

# 加载配置文件
echo "📋 加载配置文件..."
source "$CONFIG_FILE"

# 验证必要配置
required_vars=("SERVER_HOST" "SERVER_USER" "SERVER_PASSWORD" "SERVER_PATH")
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
    COMMIT_MESSAGE="部署更新 - $(date '+%Y-%m-%d %H:%M:%S')"
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

# 确认部署
echo ""
echo "� 部署信息确仓认:"
echo "   服务器: $SERVER_HOST"
echo "   用户: $SERVER_USER"
echo "   路径: $SERVER_PATH"
echo "   端口: $APP_PORT"
echo ""

read -p "确认要部署到生产服务器吗? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 部署已取消"
    exit 1
fi

# 连接服务器并执行部署
echo "🔗 连接服务器并执行部署..."

sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << EOF
set -e

echo "🔧 在服务器上执行部署..."

# 进入项目目录
cd $SERVER_PATH

# 停止应用服务
echo "⏹️  停止rwa-hub应用..."
pkill -f "python.*app.py" 2>/dev/null || echo "应用未运行"

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin $GITHUB_BRANCH

# 激活虚拟环境并启动应用
echo "🚀 启动rwa-hub应用..."
source venv/bin/activate
nohup python app.py > app.log 2>&1 &

# 等待服务启动
sleep 5

# 检查服务状态
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✅ rwa-hub应用启动成功"
    echo "🌐 应用运行在: http://$SERVER_HOST:$APP_PORT"
    
    # 测试API
    echo "🧪 测试API连接..."
    curl -s http://localhost:$APP_PORT/api/health || echo "API测试中..."
    
else
    echo "❌ 应用启动失败，请检查日志"
    tail -20 app.log
    exit 1
fi

echo "🎉 部署完成！"
EOF

# 检查部署结果
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 部署成功完成！"
    echo ""
    echo "📊 部署摘要:"
    echo "  - 服务器地址: http://$SERVER_HOST:$APP_PORT"
    echo "  - 管理后台: http://$SERVER_HOST:$APP_PORT/admin"
    echo ""
    echo "🔍 验证部署:"
    echo "  curl -s http://$SERVER_HOST:$APP_PORT/api/health"
    echo ""
    echo "📝 查看服务器日志:"
    echo "  sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && tail -f app.log'"
else
    echo ""
    echo "❌ 部署失败！请检查服务器日志"
    exit 1
fi