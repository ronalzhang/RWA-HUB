#!/bin/bash
# 工具运行器脚本，用于在正确的环境中运行资产管理工具

TOOL=$1
shift

if [ -z "$TOOL" ]; then
    echo "用法: ./run_tool.sh <工具名称> [参数...]"
    echo "支持的工具: query_asset, issue_asset, update_asset_onchain"
    exit 1
fi

# 激活虚拟环境
if [ -d "/root/RWA-HUB/venv" ]; then
    source /root/RWA-HUB/venv/bin/activate
elif [ -d "/root/RWA-HUB/tools_env" ]; then
    source /root/RWA-HUB/tools_env/bin/activate
else
    echo "错误: 找不到虚拟环境!"
    exit 1
fi

# 运行指定的工具
case $TOOL in
    query_asset)
        python3 /root/RWA-HUB/tools/query_asset.py "$@"
        ;;
    issue_asset)
        python3 /root/RWA-HUB/tools/issue_asset.py "$@"
        ;;
    update_asset_onchain)
        python3 /root/RWA-HUB/tools/update_asset_onchain.py "$@"
        ;;
    *)
        echo "未知工具: $TOOL"
        echo "支持的工具: query_asset, issue_asset, update_asset_onchain"
        exit 1
        ;;
esac

# 停用虚拟环境
deactivate
