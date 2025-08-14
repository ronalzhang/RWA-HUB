#!/bin/bash

# RWA-HUB 快速部署脚本
# 用于快速修复和部署，跳过所有确认步骤

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 RWA-HUB 快速部署${NC}"
echo "=================================="

# 加载配置
if [ -f "deploy.config" ]; then
    source deploy.config
else
    echo -e "${RED}❌ 配置文件不存在，请先运行 ./deploy.sh 创建配置${NC}"
    exit 1
fi

# 快速提交代码
echo -e "${YELLOW}📤 快速提交代码...${NC}"
if [ -n "$(git status --porcelain)" ]; then
    git add .
    git reset HEAD deploy.config 2>/dev/null || true
    git commit -m "快速修复部署 - $(date '+%Y-%m-%d %H:%M:%S')"
    git push origin ${GITHUB_BRANCH:-main}
    echo -e "${GREEN}✅ 代码已推送${NC}"
else
    echo -e "${GREEN}✅ 代码已是最新状态${NC}"
fi

# 快速部署到服务器
echo -e "${YELLOW}🔗 连接服务器部署...${NC}"
sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << EOF
set -e
cd $SERVER_PATH
echo "📥 拉取代码..."
git pull origin ${GITHUB_BRANCH:-main}
echo "🔄 重启应用..."
pm2 restart ${PM2_APP_NAME:-rwa-hub}
pm2 save
echo "✅ 部署完成"
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 快速部署成功！${NC}"
    echo -e "${BLUE}🔗 访问地址: http://$SERVER_HOST:${APP_PORT:-9000}${NC}"
else
    echo -e "${RED}❌ 部署失败${NC}"
    exit 1
fi