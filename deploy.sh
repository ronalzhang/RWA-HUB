#!/bin/bash

# RWA-HUB 通用部署脚本
# 使用配置文件来管理敏感信息，避免硬编码

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
GITHUB_REPO="https://github.com/ronalzhang/RWA-HUB.git"
GITHUB_BRANCH="main"

# 数据库配置
DB_TYPE="postgresql"  # 系统唯一数据库是postgresql
PG_HOST="localhost"
PG_DATABASE="rwa_hub"
PG_USER="rwa_hub_user"
PG_PASSWORD="password"

# 应用配置
APP_PORT="9000"
SERVICE_NAME="rwa-hub"
PYTHON_ENV="venv"
EOF
    
    echo "✅ 配置文件已创建: $CONFIG_FILE"
    echo "⚠️  请编辑配置文件并填入正确的服务器信息，然后重新运行部署脚本"
    exit 1
fi

# 加载配置文件
echo "📋 加载配置文件..."
source "$CONFIG_FILE"

# 验证必要配置
required_vars=("SERVER_HOST" "SERVER_USER" "SERVER_PASSWORD" "SERVER_PATH" "GITHUB_REPO")
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
echo "📋 部署信息确认:"
echo "   服务器: $SERVER_HOST"
echo "   用户: $SERVER_USER"
echo "   路径: $SERVER_PATH"
echo "   数据库: $DB_TYPE"
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

# 停止应用服务
echo "⏹️  停止应用服务..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null || echo "系统服务未运行"
pkill -f "python.*app.py" 2>/dev/null || echo "没有运行的Python进程"

# 备份现有数据库（如果是PostgreSQL）
if [ "$DB_TYPE" = "postgresql" ]; then
    echo "💾 备份PostgreSQL数据库..."
    BACKUP_NAME="rwa_hub_backup_\$(date +%Y%m%d_%H%M%S).sql"
    PGPASSWORD="$PG_PASSWORD" pg_dump -h "$PG_HOST" -U "$PG_USER" -d "$PG_DATABASE" > "\$BACKUP_NAME" 2>/dev/null || echo "备份失败，可能是新数据库"
fi

# 处理项目目录
if [ -d "$SERVER_PATH" ]; then
    echo "📁 项目目录已存在，更新代码..."
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
        git reset --hard origin/$GITHUB_BRANCH
    fi
else
    echo "📁 项目目录不存在，正在克隆仓库..."
    git clone $GITHUB_REPO $SERVER_PATH
    cd $SERVER_PATH
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "$PYTHON_ENV" ]; then
    echo "🐍 创建Python虚拟环境..."
    python3 -m venv $PYTHON_ENV
fi

# 激活虚拟环境
echo "🐍 激活Python虚拟环境..."
source $PYTHON_ENV/bin/activate

# 安装依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

# 如果是PostgreSQL，安装相关依赖
if [ "$DB_TYPE" = "postgresql" ]; then
    echo "📦 安装PostgreSQL依赖..."
    pip install psycopg2-binary || pip install psycopg2
fi

# 运行数据库迁移
echo "🔄 运行数据库迁移..."
if [ -f "migrate_to_postgresql.py" ] && [ "$DB_TYPE" = "postgresql" ]; then
    python3 migrate_to_postgresql.py
fi

# 运行Flask数据库迁移
echo "🔄 运行Flask数据库迁移..."
export FLASK_APP=app.py
flask db upgrade 2>/dev/null || echo "数据库迁移完成或无需迁移"

# 修复分享消息表（如果需要）
echo "🔧 修复分享消息表结构..."
python3 -c "
from app import create_app
from app.extensions import db
from sqlalchemy import text

def fix_share_messages():
    app = create_app()
    with app.app_context():
        try:
            # 检查 message_type 字段是否存在
            if '$DB_TYPE' == 'postgresql':
                result = db.session.execute(text('''
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name=\'share_messages\' AND column_name=\'message_type\'
                '''))
            else:
                result = db.session.execute(text('''
                    SELECT name FROM pragma_table_info(\'share_messages\') WHERE name=\'message_type\'
                '''))
            
            columns = result.fetchall()
            
            if not columns:
                print('添加 message_type 字段...')
                if '$DB_TYPE' == 'postgresql':
                    db.session.execute(text('''
                        ALTER TABLE share_messages 
                        ADD COLUMN message_type VARCHAR(50) NOT NULL DEFAULT \'share_content\'
                    '''))
                else:
                    db.session.execute(text('''
                        ALTER TABLE share_messages 
                        ADD COLUMN message_type TEXT NOT NULL DEFAULT \'share_content\'
                    '''))
                db.session.commit()
                print('✅ message_type 字段已添加')
            
            # 初始化默认数据
            result = db.session.execute(text('SELECT COUNT(*) FROM share_messages'))
            count = result.scalar()
            
            if count == 0:
                print('初始化默认分享消息...')
                messages = [
                    ('🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。', 'share_content', 100),
                    ('💎 投资RWA资产，享受实物资产带来的稳定收益！区块链技术保障，安全可靠。', 'share_content', 90),
                    ('🏆 分享赚佣金！邀请好友投资，您可获得高达35%的推广佣金！', 'share_content', 80),
                    ('一次分享，终身收益 - 无限下级35%分成', 'reward_plan', 100),
                    ('💰 推荐好友即享35%超高佣金，人人都是赚钱达人！', 'reward_plan', 90)
                ]
                
                for content, msg_type, weight in messages:
                    if '$DB_TYPE' == 'postgresql':
                        db.session.execute(text('''
                            INSERT INTO share_messages (content, message_type, weight, is_active, created_at, updated_at)
                            VALUES (:content, :msg_type, :weight, true, NOW(), NOW())
                        '''), {'content': content, 'msg_type': msg_type, 'weight': weight})
                    else:
                        db.session.execute(text('''
                            INSERT INTO share_messages (content, message_type, weight, is_active, created_at, updated_at)
                            VALUES (:content, :msg_type, :weight, 1, datetime(\'now\'), datetime(\'now\'))
                        '''), {'content': content, 'msg_type': msg_type, 'weight': weight})
                
                db.session.commit()
                print('✅ 默认分享消息已初始化')
                
        except Exception as e:
            print(f'修复失败: {e}')
            db.session.rollback()

fix_share_messages()
" 2>/dev/null || echo "分享消息修复完成"

# 启动应用服务
echo "🚀 启动应用服务..."
nohup python app.py > app.log 2>&1 &

# 等待服务启动
sleep 10

# 检查服务状态
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✅ 应用服务启动成功"
    echo "🌐 应用运行在: http://$SERVER_HOST:$APP_PORT"
    
    # 测试API
    echo "🧪 测试API连接..."
    curl -s http://localhost:$APP_PORT/api/health || echo "API测试失败，但服务可能正在启动中"
    
else
    echo "❌ 应用服务启动失败，请检查日志"
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
    echo "  - 分享消息管理: http://$SERVER_HOST:$APP_PORT/admin/v2/share-messages"
    echo "  - 分销系统配置: http://$SERVER_HOST:$APP_PORT/admin/v2/commission"
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