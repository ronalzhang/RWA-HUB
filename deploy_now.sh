#!/bin/bash

# 简化的RWA-HUB生产服务器部署脚本
# 需要手动输入服务器密码

echo "🚀 开始部署RWA-HUB到生产服务器"
echo "服务器: 156.236.74.200"
echo "目录: /root/RWA-HUB"
echo ""

# 检查本地环境
if [ ! -f "app.py" ] || [ ! -d "app" ]; then
    echo "❌ 请在RWA-HUB项目根目录执行此脚本"
    exit 1
fi

echo "✅ 本地环境检查通过"

# 创建临时部署目录
TEMP_DIR="/tmp/rwa-deploy-$(date +%s)"
mkdir -p "$TEMP_DIR"

echo "📦 准备部署文件..."

# 复制项目文件
rsync -av --progress \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='node_modules' \
    --exclude='*.log' \
    --exclude='backup' \
    --exclude='logs' \
    --exclude='test' \
    --exclude='tests' \
    --exclude='deploy*.sh' \
    --exclude='/tmp' \
    ./ "$TEMP_DIR/"

# 创建服务器部署脚本
cat > "$TEMP_DIR/server_deploy.sh" << 'EOF'
#!/bin/bash
set -e

echo "🔧 开始服务器端部署..."

# 备份现有系统
BACKUP_DIR="/root/RWA-HUB-backup-$(date +%Y%m%d_%H%M%S)"
if [ -d "/root/RWA-HUB" ]; then
    echo "📦 创建备份: $BACKUP_DIR"
    cp -r /root/RWA-HUB "$BACKUP_DIR"
fi

# 停止服务
echo "🛑 停止现有服务..."
pm2 stop rwa-hub || true
pkill -f "python.*app.py" || true

# 部署新代码
echo "📁 部署新代码..."
rm -rf /root/RWA-HUB
mv /tmp/rwa-deploy /root/RWA-HUB
cd /root/RWA-HUB

# 设置权限
chmod +x *.py
mkdir -p logs instance backup

# 安装依赖
echo "📦 安装依赖..."
python3 -m pip install -r requirements.txt

# 创建PM2配置
cat > ecosystem.config.json << EOFPM2
{
  "apps": [{
    "name": "rwa-hub",
    "script": "app.py",
    "interpreter": "python3",
    "cwd": "/root/RWA-HUB",
    "instances": 1,
    "autorestart": true,
    "watch": false,
    "max_memory_restart": "1G",
    "env": {
      "FLASK_ENV": "production",
      "PORT": "9000"
    },
    "error_file": "./logs/err.log",
    "out_file": "./logs/out.log",
    "log_file": "./logs/combined.log"
  }]
}
EOFPM2

# 启动服务
echo "🚀 启动服务..."
pm2 start ecosystem.config.json
pm2 save

sleep 5

# 验证部署
if pm2 list | grep -q "rwa-hub.*online"; then
    echo "✅ 服务启动成功"
else
    echo "❌ 服务启动失败"
    exit 1
fi

echo ""
echo "🎉 部署完成！"
echo "🌐 访问地址: http://156.236.74.200:9000"
echo "🔧 管理后台: http://156.236.74.200:9000/admin/v2"
echo "💾 备份位置: $BACKUP_DIR"

# 创建回滚脚本
cat > /root/rollback.sh << EOFROLLBACK
#!/bin/bash
echo "🔄 回滚系统..."
pm2 stop rwa-hub
rm -rf /root/RWA-HUB
mv "$BACKUP_DIR" /root/RWA-HUB
cd /root/RWA-HUB
pm2 start rwa-hub
echo "✅ 回滚完成"
EOFROLLBACK

chmod +x /root/rollback.sh
echo "📝 回滚脚本: /root/rollback.sh"
EOF

chmod +x "$TEMP_DIR/server_deploy.sh"

echo "📤 上传文件到服务器..."
echo "请输入服务器密码："

# 上传文件
scp -r "$TEMP_DIR" root@156.236.74.200:/tmp/rwa-deploy

echo "🔧 在服务器上执行部署..."
echo "请再次输入服务器密码："

# 执行部署
ssh root@156.236.74.200 "chmod +x /tmp/rwa-deploy/server_deploy.sh && /tmp/rwa-deploy/server_deploy.sh"

# 清理临时文件
rm -rf "$TEMP_DIR"

echo ""
echo "🎉 部署流程完成！"
echo "🔍 运行状态检查："
echo "python3 check_production_server.py"