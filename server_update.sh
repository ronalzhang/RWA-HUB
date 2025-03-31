#!/bin/bash

# 加载环境变量
set -e

echo "开始服务器更新流程..."

# 进入项目目录
cd /root/RWA-HUB/

# 获取最新代码
echo "拉取最新代码..."
git pull

# 确保vendor目录存在
echo "创建vendor目录..."
mkdir -p app/static/vendor/webfonts

# 创建必要的符号链接
echo "创建符号链接..."
if [ -f app/static/vendor/solana-web3.min.js ]; then
  ln -sf solana-web3.min.js app/static/vendor/solana-web3.js
  ln -sf solana-web3.min.js app/static/vendor/solana-web3-stable.js
fi

# 根据需要下载静态资源...

# 终止当前运行的应用
echo "停止当前应用进程..."
pkill -f "python /root/RWA-HUB/run.py" || echo "没有找到运行中的应用进程"

# 激活Python虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 运行应用
echo "启动应用..."
nohup python run.py > logs/app_restart.log 2>&1 &

echo "等待应用启动..."
sleep 5

# 检查应用是否成功启动
if pgrep -f "python /root/RWA-HUB/run.py" > /dev/null; then
    echo "应用已成功启动！"
else
    echo "警告：应用启动可能失败，请检查日志"
    tail -n 20 logs/app_restart.log
fi

echo "更新流程完成！" 