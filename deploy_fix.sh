#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # 无颜色

echo -e "${YELLOW}开始部署钱包修复脚本...${NC}"

# 服务器信息
SERVER="47.236.39.134"
SSH_KEY="vincent.pem"
REMOTE_USER="root"
PROJECT_DIR="/www/wwwroot/RWA-HUB_4.0" # 服务器上的项目目录
STATIC_JS_DIR="${PROJECT_DIR}/app/static/js"
TEMPLATES_DIR="${PROJECT_DIR}/app/templates"

# 本地文件
LOCAL_WALLET_FIX="wallet_fix.js"

# 检查本地文件是否存在
if [ ! -f "${LOCAL_WALLET_FIX}" ]; then
    echo -e "${RED}错误: 本地钱包修复脚本 ${LOCAL_WALLET_FIX} 不存在${NC}"
    exit 1
fi

echo -e "${GREEN}钱包修复脚本已找到，准备上传...${NC}"

# 1. 上传钱包修复脚本到服务器的静态JS目录
echo -e "${YELLOW}上传钱包修复脚本到服务器...${NC}"
scp -i ${SSH_KEY} ${LOCAL_WALLET_FIX} ${REMOTE_USER}@${SERVER}:${STATIC_JS_DIR}/

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 上传钱包修复脚本失败${NC}"
    exit 1
fi

echo -e "${GREEN}钱包修复脚本已成功上传到 ${STATIC_JS_DIR}/${LOCAL_WALLET_FIX}${NC}"

# 2. 修改base.html文件，添加钱包修复脚本引用
echo -e "${YELLOW}修改base.html文件，添加钱包修复脚本引用...${NC}"

# 创建备份
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "cp ${TEMPLATES_DIR}/base.html ${TEMPLATES_DIR}/base.html.bak_$(date +%Y%m%d_%H%M%S)"

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 创建base.html备份失败${NC}"
    exit 1
fi

# 添加脚本引用到wallet.js之后
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "sed -i '/static.*wallet.js/a \    <script src=\"{{ url_for(\"static\", filename=\"js/wallet_fix.js\") }}\"></script>' ${TEMPLATES_DIR}/base.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 修改base.html添加脚本引用失败${NC}"
    exit 1
fi

echo -e "${GREEN}base.html已成功修改，添加了钱包修复脚本引用${NC}"

# 3. 检查并修复文件权限
echo -e "${YELLOW}检查并修复文件权限...${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "chmod 644 ${STATIC_JS_DIR}/${LOCAL_WALLET_FIX}"

if [ $? -ne 0 ]; then
    echo -e "${RED}警告: 修复文件权限失败，可能需要手动设置${NC}"
fi

# 4. 重启应用服务
echo -e "${YELLOW}重启应用服务...${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "supervisorctl restart rwahub"

if [ $? -ne 0 ]; then
    echo -e "${RED}警告: 重启应用服务失败，可能需要手动重启${NC}"
    echo -e "${YELLOW}尝试使用其他方式重启...${NC}"
    ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "cd ${PROJECT_DIR} && ./.restart.sh"
fi

# 5. 验证修复是否生效
echo -e "${YELLOW}验证修复是否生效...${NC}"
echo -e "${GREEN}请等待应用重启完成（约10-20秒）...${NC}"
sleep 15

echo -e "${YELLOW}检查应用是否正常运行...${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "curl -s -o /dev/null -w '%{http_code}' localhost:5000/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}应用已成功重启并响应HTTP请求${NC}"
else
    echo -e "${RED}警告: 应用可能未正常启动，请手动检查${NC}"
fi

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}修复脚本部署完成！${NC}"
echo -e "${GREEN}请测试以下功能:${NC}"
echo -e "${GREEN}1. 钱包连接状态检测${NC}"
echo -e "${GREEN}2. 购买按钮状态更新${NC}"
echo -e "${GREEN}3. 购买流程${NC}"
echo -e "${GREEN}===========================================${NC}" 