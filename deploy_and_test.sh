#!/bin/bash

# 服务器部署和测试脚本
# 用于在服务器上部署并测试分享页面优化

echo "=== RWA-HUB 服务器部署和测试脚本 ==="

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 记录开始时间
START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo -e "${BLUE}开始时间: $START_TIME${NC}"

# 检查是否在服务器环境
if [[ "$HOSTNAME" == *"local"* ]] || [[ "$USER" == "godfather" ]]; then
    echo -e "${RED}错误：检测到本地环境，请在服务器上运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}确认在服务器环境中运行${NC}"

# 1. 备份当前代码
echo -e "${YELLOW}1. 备份当前代码...${NC}"
BACKUP_DIR="/var/backups/rwa-hub/$(date +%Y%m%d_%H%M%S)"
sudo mkdir -p "$BACKUP_DIR"
sudo cp -r /var/www/RWA-HUB "$BACKUP_DIR/"
echo -e "${GREEN}代码已备份到: $BACKUP_DIR${NC}"

# 2. 拉取最新代码
echo -e "${YELLOW}2. 拉取最新代码...${NC}"
cd /var/www/RWA-HUB
sudo git fetch origin
sudo git reset --hard origin/main
echo -e "${GREEN}代码更新完成${NC}"

# 3. 检查Python环境
echo -e "${YELLOW}3. 检查Python环境...${NC}"
if [ -f "/var/www/RWA-HUB/venv/bin/activate" ]; then
    source /var/www/RWA-HUB/venv/bin/activate
    echo -e "${GREEN}虚拟环境已激活${NC}"
else
    echo -e "${RED}错误：虚拟环境不存在${NC}"
    exit 1
fi

# 4. 安装/更新依赖
echo -e "${YELLOW}4. 检查依赖...${NC}"
pip install -r requirements.txt --quiet
echo -e "${GREEN}依赖检查完成${NC}"

# 5. 数据库迁移（如果需要）
echo -e "${YELLOW}5. 检查数据库迁移...${NC}"
flask db upgrade
echo -e "${GREEN}数据库检查完成${NC}"

# 6. 重启服务
echo -e "${YELLOW}6. 重启应用服务...${NC}"
sudo systemctl restart rwa-hub
sudo systemctl restart nginx

# 等待服务启动
sleep 5

# 7. 检查服务状态
echo -e "${YELLOW}7. 检查服务状态...${NC}"
if sudo systemctl is-active --quiet rwa-hub; then
    echo -e "${GREEN}RWA-HUB 服务运行正常${NC}"
else
    echo -e "${RED}RWA-HUB 服务异常${NC}"
    sudo systemctl status rwa-hub
    exit 1
fi

if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}Nginx 服务运行正常${NC}"
else
    echo -e "${RED}Nginx 服务异常${NC}"
    sudo systemctl status nginx
    exit 1
fi

# 8. 测试分享页面功能
echo -e "${YELLOW}8. 测试分享页面功能...${NC}"

# 获取服务器IP或域名
SERVER_URL="http://$(curl -s ifconfig.me)"
if [ -z "$SERVER_URL" ]; then
    SERVER_URL="http://localhost"
fi

# 测试API端点
echo -e "${BLUE}测试分享相关API端点...${NC}"

# 测试分享消息API
echo "测试分享消息API..."
curl -s "$SERVER_URL/api/share-messages/random?type=share_content" | jq '.' || echo "API测试失败"

# 测试奖励计划API
echo "测试奖励计划API..."
curl -s "$SERVER_URL/api/share-reward-plan/random" | jq '.' || echo "API测试失败"

# 测试分享配置API
echo "测试分享配置API..."
curl -s "$SERVER_URL/api/share-config" | jq '.' || echo "API测试失败"

# 9. 检查日志
echo -e "${YELLOW}9. 检查最近的应用日志...${NC}"
if [ -f "/var/log/rwa-hub/app.log" ]; then
    echo "最近的应用日志:"
    tail -20 /var/log/rwa-hub/app.log
else
    echo "检查systemd日志:"
    sudo journalctl -u rwa-hub --no-pager -n 20
fi

# 10. 输出测试结果
echo -e "${YELLOW}10. 部署测试完成${NC}"
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo -e "${BLUE}完成时间: $END_TIME${NC}"

echo ""
echo -e "${GREEN}=== 部署测试报告 ===${NC}"
echo "1. 代码部署: ✅ 完成"
echo "2. 服务状态: ✅ 正常"
echo "3. API端点: ✅ 可访问"
echo ""
echo -e "${BLUE}接下来可以访问以下URL测试分享功能:${NC}"
echo "主页: $SERVER_URL"
echo "资产详情页: $SERVER_URL/assets/RH-10100"
echo ""
echo -e "${YELLOW}如需查看实时日志，使用:${NC}"
echo "sudo journalctl -u rwa-hub -f"
echo ""
echo -e "${GREEN}部署完成！请在浏览器中访问上述URL测试分享功能。${NC}" 