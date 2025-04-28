#!/bin/bash

# 部署wallet_debug.js脚本修复

# 配置参数
SERVER="47.236.39.134"
SSH_KEY="vincent.pem"
REMOTE_USER="root"
STATIC_DIR="/var/www/html/app/static/js"
TEMPLATES_DIR="/var/www/html/app/templates"
LOCAL_JS="app/static/js/wallet_debug.js"

# 显示脚本信息
echo "=== 钱包调试脚本部署工具 ==="
echo "服务器: ${SERVER}"
echo "静态资源目录: ${STATIC_DIR}"
echo "模板目录: ${TEMPLATES_DIR}"

# 检查本地文件是否存在
if [ ! -f "${LOCAL_JS}" ]; then
    echo "错误: 本地文件 ${LOCAL_JS} 不存在!"
    exit 1
fi

echo "=== 步骤1: 上传钱包调试脚本 ==="
scp -i ${SSH_KEY} ${LOCAL_JS} ${REMOTE_USER}@${SERVER}:${STATIC_DIR}/wallet_debug.js
if [ $? -ne 0 ]; then
    echo "错误: 上传文件失败!"
    exit 1
fi
echo "✓ 钱包调试脚本上传成功"

echo "=== 步骤2: 检查base.html中的脚本引用 ==="
# 检查是否已存在wallet_debug.js的引用
REFS_COUNT=$(ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "grep -c 'wallet_debug.js' ${TEMPLATES_DIR}/base.html")
if [ $REFS_COUNT -gt 0 ]; then
    echo "✓ base.html中已存在wallet_debug.js的引用 (${REFS_COUNT}处)"
else
    echo "将wallet_debug.js引用添加到base.html中..."
    # 在wallet_fix.js后添加脚本引用
    ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "sed -i '/static.*wallet_fix.js/a \    <script src=\"{{ url_for(\"static\", filename=\"js/wallet_debug.js\") }}\"></script>' ${TEMPLATES_DIR}/base.html"
    if [ $? -ne 0 ]; then
        echo "错误: 添加脚本引用失败!"
        exit 1
    fi
    echo "✓ 脚本引用添加成功"
fi

echo "=== 步骤3: 验证部署 ==="
# 检查静态资源是否上传成功
FILE_SIZE=$(ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "stat --format=%s ${STATIC_DIR}/wallet_debug.js")
if [ $? -ne 0 ] || [ -z "$FILE_SIZE" ] || [ "$FILE_SIZE" -lt 100 ]; then
    echo "错误: 验证文件大小失败! 获取到的大小: ${FILE_SIZE}"
    exit 1
fi
echo "✓ 钱包调试脚本大小正常: ${FILE_SIZE} 字节"

# 验证引用是否成功
REFS_COUNT=$(ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "grep -c 'wallet_debug.js' ${TEMPLATES_DIR}/base.html")
if [ $REFS_COUNT -gt 0 ]; then
    echo "✓ base.html中引用验证成功 (${REFS_COUNT}处)"
else
    echo "错误: base.html中找不到wallet_debug.js的引用!"
    exit 1
fi

echo "=== 钱包调试脚本部署完成! ==="
echo "文件位置: ${STATIC_DIR}/wallet_debug.js"
echo "引用位置: ${TEMPLATES_DIR}/base.html"
echo "注意: 可能需要等待几分钟或重启应用以使更改生效" 