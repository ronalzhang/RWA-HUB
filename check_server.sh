#!/bin/bash

# RWA-HUB 服务器状态检查脚本

# 服务器配置
SERVER_HOST="156.236.74.200"
SERVER_USER="root"
SERVER_PASSWORD="Pr971V3j"
PM2_APP_NAME="rwa-hub"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 RWA-HUB 服务器状态检查${NC}"
echo "=================================="

# 检查API健康状态
echo -e "\n${YELLOW}📊 API健康状态检查:${NC}"
curl -s http://$SERVER_HOST:9000/api/health/ | jq '.overall_status' 2>/dev/null || echo "API检查失败"

# 检查PM2状态
echo -e "\n${YELLOW}🔧 PM2应用状态:${NC}"
sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << 'EOF'
if command -v pm2 &> /dev/null; then
    pm2 list | grep -E "(App name|rwa-hub)" --color=never
else
    echo "PM2未安装"
fi
EOF

# 显示最近日志
echo -e "\n${YELLOW}📝 最近10条应用日志:${NC}"
sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << EOF
if command -v pm2 &> /dev/null && pm2 list | grep -q "$PM2_APP_NAME"; then
    echo "=== PM2 输出日志 ==="
    pm2 logs $PM2_APP_NAME --lines 5 --nostream | tail -10
    echo ""
    echo "=== PM2 错误日志 ==="
    pm2 logs $PM2_APP_NAME --err --lines 5 --nostream | tail -10
else
    echo "使用传统日志方式..."
    cd /root/RWA-HUB && tail -10 app.log 2>/dev/null || echo "日志文件不存在"
fi
EOF

# 显示系统资源使用情况
echo -e "\n${YELLOW}💻 系统资源使用:${NC}"
sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << 'EOF'
echo "CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
echo "内存使用: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
echo "磁盘使用: $(df -h / | awk 'NR==2{print $5}')"
EOF

echo -e "\n${GREEN}✅ 检查完成${NC}"
echo ""
echo -e "${BLUE}🔗 快捷链接:${NC}"
echo "  - 主页: http://$SERVER_HOST:9000"
echo "  - 管理后台: http://$SERVER_HOST:9000/admin"
echo "  - API健康检查: http://$SERVER_HOST:9000/api/health/"
echo ""
echo -e "${BLUE}📝 常用命令:${NC}"
echo "  - 查看实时日志: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'pm2 logs $PM2_APP_NAME -f'"
echo "  - 重启应用: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'pm2 restart $PM2_APP_NAME'"
echo "  - PM2状态: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'pm2 status'"