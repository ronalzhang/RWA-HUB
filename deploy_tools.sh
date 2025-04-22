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
APP_DIR="/root/RWA-HUB"
VENV_DIR="/root/RWA-HUB/venv"

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

# 安装依赖并设置应用环境
echo "设置应用环境并安装依赖..."
ssh -i "$SSH_KEY" root@"$SERVER_IP" << EOF
    # 检查Python版本
    python3 --version
    
    # 使用现有的虚拟环境安装依赖
    if [ -d "$VENV_DIR" ]; then
        echo "使用应用现有的虚拟环境..."
        source $VENV_DIR/bin/activate
        pip install sqlalchemy psycopg2-binary python-dotenv
        deactivate
    else
        echo "警告: 应用虚拟环境不存在，创建新的虚拟环境..."
        cd $APP_DIR
        python3 -m venv tools_env
        source tools_env/bin/activate
        pip install sqlalchemy psycopg2-binary python-dotenv
        deactivate
    fi
    
    # 创建工具运行器脚本
    cat > $APP_DIR/run_tool.sh << 'TOOLSCRIPT'
#!/bin/bash
# 工具运行器脚本，用于在正确的环境中运行资产管理工具

TOOL=\$1
shift

if [ -z "\$TOOL" ]; then
    echo "用法: ./run_tool.sh <工具名称> [参数...]"
    echo "支持的工具: query_asset, issue_asset, update_asset_onchain"
    exit 1
fi

# 激活虚拟环境
if [ -d "$VENV_DIR" ]; then
    source $VENV_DIR/bin/activate
elif [ -d "$APP_DIR/tools_env" ]; then
    source $APP_DIR/tools_env/bin/activate
else
    echo "错误: 找不到虚拟环境!"
    exit 1
fi

# 运行指定的工具
case \$TOOL in
    query_asset)
        python3 $REMOTE_DIR/query_asset.py "\$@"
        ;;
    issue_asset)
        python3 $REMOTE_DIR/issue_asset.py "\$@"
        ;;
    update_asset_onchain)
        python3 $REMOTE_DIR/update_asset_onchain.py "\$@"
        ;;
    *)
        echo "未知工具: \$TOOL"
        echo "支持的工具: query_asset, issue_asset, update_asset_onchain"
        exit 1
        ;;
esac

# 停用虚拟环境
deactivate
TOOLSCRIPT

    # 设置执行权限
    chmod +x $APP_DIR/run_tool.sh
    
    # 创建快捷命令脚本
    ln -sf $APP_DIR/run_tool.sh /usr/local/bin/rwa-tool
    
    echo "工具环境设置完成"
EOF

echo "======================"
echo "部署完成!"
echo "工具已部署到 $SERVER_IP:$REMOTE_DIR"
echo "可以通过以下方式使用工具:"
echo "1. SSH登录服务器:"
echo "   ssh -i $SSH_KEY root@$SERVER_IP"
echo "2. 执行工具命令:"
echo "   rwa-tool query_asset [代币符号]"
echo "   rwa-tool issue_asset --name \"资产名称\" --type real_estate --blockchain ethereum --issuer 0x123..."
echo "   rwa-tool update_asset_onchain update --token 符号 --contract 合约地址"
echo "======================"

exit 0 