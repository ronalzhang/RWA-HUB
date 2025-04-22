#!/bin/bash

# 脚本用于将资产管理工具部署到远程服务器
# 使用方法: ./deploy_tools.sh <server_ip> <ssh_key>

# 检查参数
if [ $# -lt 2 ]; then
    echo "用法: $0 <server_ip> <ssh_key>"
    echo "示例: $0 47.236.39.134 vincent.pem"
    exit 1
fi

SERVER_IP=$1
SSH_KEY=$2
REMOTE_DIR="/root/RWA-HUB/tools"

echo "======================"
echo "开始部署资产管理工具..."
echo "======================"

# 检查本地文件是否存在
FILES=(
    "issue_asset.py"
    "query_asset.py"
    "update_asset_onchain.py"
    "SCRIPTS_README.md"
)

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "错误: 本地文件 $file 不存在!"
        exit 1
    fi
done

# 创建远程目录
echo "创建远程目录 $REMOTE_DIR (如果不存在)..."
ssh -i "$SSH_KEY" root@"$SERVER_IP" "mkdir -p $REMOTE_DIR"

# 复制文件到远程服务器
echo "正在复制文件到远程服务器..."
scp -i "$SSH_KEY" "${FILES[@]}" root@"$SERVER_IP":"$REMOTE_DIR"/

# 设置执行权限
echo "设置执行权限..."
ssh -i "$SSH_KEY" root@"$SERVER_IP" "chmod +x $REMOTE_DIR/*.py"

# 检查远程服务器上的Python环境和依赖
echo "检查Python环境和依赖..."
ssh -i "$SSH_KEY" root@"$SERVER_IP" << EOF
    cd "$REMOTE_DIR"
    # 检查Python版本
    python3 --version
    
    # 安装必要的依赖
    pip3 install sqlalchemy psycopg2-binary python-dotenv
    
    # 创建符号链接到应用根目录
    cd /root/RWA-HUB
    ln -sf $REMOTE_DIR/issue_asset.py .
    ln -sf $REMOTE_DIR/query_asset.py .
    ln -sf $REMOTE_DIR/update_asset_onchain.py .
    
    echo "依赖安装完成，工具已准备就绪"
EOF

echo "======================"
echo "部署完成!"
echo "工具已部署到 $SERVER_IP:$REMOTE_DIR"
echo "可以通过SSH登录服务器使用这些工具:"
echo "  ssh -i $SSH_KEY root@$SERVER_IP"
echo "  cd /root/RWA-HUB"
echo "  python3 query_asset.py [代币符号]"
echo "======================"

exit 0 