#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 服务器信息
SERVER="47.236.39.134"
SSH_KEY="vincent.pem"
REMOTE_USER="root"
PROJECT_DIR="/root/RWA-HUB"

echo -e "${YELLOW}========== RWA-HUB 服务器状态检查 ==========${NC}"

# 1. 检查服务器负载和内存使用情况
echo -e "${BLUE}【系统状态】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "uptime && free -h && df -h | grep -v tmpfs"

echo ""

# 2. 检查PM2应用进程状态
echo -e "${BLUE}【PM2应用状态】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "pm2 list"

echo ""

# 3. 检查Python进程
echo -e "${BLUE}【Python进程】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "ps aux | grep -E 'python|flask|waitress|gunicorn' | grep -v grep"

echo ""

# 4. 检查网站响应状态
echo -e "${BLUE}【网站响应】${NC}"
echo -e "检查主页响应..."
RESPONSE=$(ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "curl -s -o /dev/null -w '%{http_code}' localhost:5000/")
if [ "$RESPONSE" == "200" ]; then
    echo -e "${GREEN}主页响应正常 (HTTP 200)${NC}"
else
    echo -e "${RED}主页响应异常 (HTTP $RESPONSE)${NC}"
fi

echo ""

# 5. 检查日志文件中的错误
echo -e "${BLUE}【最近错误日志】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "tail -n 50 ${PROJECT_DIR}/app.log | grep -i error"

echo ""

# 6. 检查PM2日志
echo -e "${BLUE}【PM2日志】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "pm2 logs --lines 20 rwa-hub"

echo ""

# 7. 检查钱包修复脚本是否存在
echo -e "${BLUE}【钱包修复脚本】${NC}"
SCRIPT_EXISTS=$(ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "if [ -f ${PROJECT_DIR}/app/static/js/wallet_fix.js ]; then echo 'yes'; else echo 'no'; fi")

if [ "$SCRIPT_EXISTS" == "yes" ]; then
    echo -e "${GREEN}钱包修复脚本已存在${NC}"
    
    # 检查脚本文件大小和修改时间
    ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "ls -la ${PROJECT_DIR}/app/static/js/wallet_fix.js"
    
    # 检查base.html是否包含脚本引用
    SCRIPT_REFERENCED=$(ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "grep -c 'wallet_fix.js' ${PROJECT_DIR}/app/templates/base.html")
    
    if [ "$SCRIPT_REFERENCED" -gt 0 ]; then
        echo -e "${GREEN}base.html已引用修复脚本 (找到 $SCRIPT_REFERENCED 处引用)${NC}"
    else
        echo -e "${RED}base.html未引用修复脚本${NC}"
    fi
else
    echo -e "${RED}钱包修复脚本不存在${NC}"
fi

echo ""

# 8. 检查服务器启动和运行时间
echo -e "${BLUE}【服务器运行时间】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "uptime -p"

echo ""

# 9. 检查网络连接
echo -e "${BLUE}【活跃网络连接】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "netstat -tulpn | grep -E ':(80|443|5000)' | grep -v grep"

echo ""

# 10. 检查修复前后的页面响应速度
echo -e "${BLUE}【页面响应时间】${NC}"
ssh -i ${SSH_KEY} ${REMOTE_USER}@${SERVER} "curl -s -w '总响应时间: %{time_total}秒\n' -o /dev/null localhost:5000/"

echo -e "${YELLOW}========== 检查完成 ==========${NC}" 