#!/bin/bash

# 基于GitHub仓库的PostgreSQL数据迁移部署脚本
# 1. 提交代码到GitHub仓库
# 2. 使用sshpass连接服务器
# 3. 在服务器上拉取最新代码并执行迁移

set -e

# 服务器配置
SERVER_PASSWORD="Pr971V3j"
SERVER_USER="root"
SERVER_HOST="156.236.74.200"
SERVER_PATH="/root/RWA-HUB"
GITHUB_REPO="https://github.com/ronalzhang/RWA-HUB.git"

# PostgreSQL 配置
PG_HOST="localhost"
PG_DATABASE="rwa_hub"
PG_USER="rwa_hub_user"
PG_PASSWORD="password"

echo "🚀 开始基于GitHub的PostgreSQL数据迁移部署..."

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

# 检查本地文件
echo "🔍 检查本地迁移文件..."
required_files=(
    "migrate_to_postgresql.py"
    "verify_postgresql_migration.py"
    "rwa_hub_data_export.sql"
    "manual_server_deployment_guide.md"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少必要文件: $file"
        exit 1
    fi
done

echo "✅ 本地文件检查完成"

# 验证SQL导出文件
echo "🔍 验证SQL导出文件..."
RECORD_COUNT=$(grep -c "INSERT INTO" rwa_hub_data_export.sql || echo "0")
echo "📊 SQL文件包含 $RECORD_COUNT 条INSERT语句"

if [ "$RECORD_COUNT" -lt 100 ]; then
    echo "⚠️  SQL文件记录数较少，请确认数据完整性"
    read -p "是否继续部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 部署已取消"
        exit 1
    fi
fi

# 提交代码到GitHub
echo "📤 提交代码到GitHub仓库..."

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 发现未提交的更改，正在提交..."
    
    # 添加所有更改
    git add .
    
    # 提交更改
    COMMIT_MESSAGE="PostgreSQL数据迁移部署 - $(date '+%Y-%m-%d %H:%M:%S')"
    git commit -m "$COMMIT_MESSAGE"
    
    echo "✅ 代码已提交: $COMMIT_MESSAGE"
else
    echo "✅ 代码已是最新状态"
fi

# 推送到远程仓库
echo "🔄 推送到远程仓库..."
git push origin main || git push origin master || {
    echo "❌ 推送失败，请检查GitHub仓库配置"
    exit 1
}

echo "✅ 代码已推送到GitHub"

# 确认部署
echo ""
echo "📋 部署信息确认:"
echo "   服务器: $SERVER_HOST"
echo "   用户: $SERVER_USER"
echo "   路径: $SERVER_PATH"
echo "   数据库: $PG_DATABASE"
echo "   预期迁移记录数: $RECORD_COUNT"
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

echo "🔧 在服务器上执行PostgreSQL数据迁移..."

# 停止应用服务
echo "⏹️  停止应用服务..."
sudo systemctl stop rwa-hub || echo "服务未运行"
pkill -f "python.*app.py" || echo "没有运行的Python进程"

# 备份现有数据库
echo "💾 备份现有PostgreSQL数据库..."
BACKUP_NAME="rwa_hub_backup_\$(date +%Y%m%d_%H%M%S).sql"
PGPASSWORD="$PG_PASSWORD" pg_dump -h "$PG_HOST" -U "$PG_USER" -d "$PG_DATABASE" > "\$BACKUP_NAME" 2>/dev/null || echo "备份失败，可能是新数据库"

# 处理项目目录
if [ -d "$SERVER_PATH" ]; then
    echo "📁 项目目录已存在，检查Git仓库状态..."
    cd $SERVER_PATH
    
    # 检查是否是Git仓库
    if [ ! -d ".git" ]; then
        echo "🔄 不是Git仓库，重新初始化..."
        cd ..
        rm -rf $SERVER_PATH
        git clone $GITHUB_REPO $SERVER_PATH
        cd $SERVER_PATH
    else
        echo "📥 拉取最新代码..."
        git fetch origin
        git reset --hard origin/main || git reset --hard origin/master
    fi
else
    echo "📁 项目目录不存在，正在克隆仓库..."
    git clone $GITHUB_REPO $SERVER_PATH
    cd $SERVER_PATH
fi

# 检查PostgreSQL连接
echo "🔍 检查PostgreSQL连接..."
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DATABASE" -c "SELECT version();" || {
    echo "❌ 无法连接到PostgreSQL数据库"
    exit 1
}

# 激活虚拟环境
echo "🐍 激活Python虚拟环境..."
source venv/bin/activate

# 安装PostgreSQL依赖
echo "📦 安装PostgreSQL依赖..."
pip install psycopg2-binary || pip install psycopg2

# 运行数据迁移
echo "🔄 运行PostgreSQL数据迁移..."
python3 migrate_to_postgresql.py

# 验证迁移结果
echo "🔍 验证迁移结果..."
python3 verify_postgresql_migration.py

# 运行数据库迁移（Flask）
echo "🔄 运行Flask数据库迁移..."
flask db upgrade || echo "数据库迁移完成或无需迁移"

# 启动应用服务
echo "🚀 启动应用服务..."
nohup python app.py > app.log 2>&1 &

# 等待服务启动
sleep 10

# 检查服务状态
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✅ 应用服务启动成功"
    echo "🌐 应用运行在: http://$SERVER_HOST:9000"
    
    # 测试API
    echo "🧪 测试API连接..."
    curl -s http://localhost:9000/api/health || echo "API测试失败，但服务可能正在启动中"
    
else
    echo "❌ 应用服务启动失败，请检查日志"
    tail -20 app.log
    exit 1
fi

echo "🎉 PostgreSQL数据迁移部署完成！"
EOF

# 检查部署结果
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 部署成功完成！"
    echo ""
    echo "📊 部署摘要:"
    echo "  - 数据库类型: PostgreSQL"
    echo "  - 迁移记录数: $RECORD_COUNT"
    echo "  - 服务器地址: http://$SERVER_HOST:9000"
    echo "  - 管理后台: http://$SERVER_HOST:9000/admin"
    echo ""
    echo "🔍 验证部署:"
    echo "  curl -s http://$SERVER_HOST:9000/api/health"
    echo ""
    echo "📝 查看服务器日志:"
    echo "  sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && tail -f app.log'"
    echo ""
    echo "🗄️ 连接数据库:"
    echo "  sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST"
    echo "  PGPASSWORD=$PG_PASSWORD psql -h localhost -U $PG_USER -d $PG_DATABASE"
else
    echo ""
    echo "❌ 部署失败！请检查服务器日志"
    echo ""
    echo "📝 查看错误日志:"
    echo "  sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && tail -50 app.log'"
    exit 1
fi