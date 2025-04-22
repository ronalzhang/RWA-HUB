
# 设置工作目录
cd /root/RWA-HUB

# 终止当前运行的应用
echo "停止当前应用进程..."
pkill -f "python /root/RWA-HUB/run.py" || echo "没有找到运行中的应用进程"

# 激活Python虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 运行应用
echo "启动应用..."
nohup python run.py > logs/app_restart.log 2>&1 &

# 等待应用启动
echo "等待应用启动..."
sleep 3

# 检查应用是否成功启动
if pgrep -f "python /root/RWA-HUB/run.py" > /dev/null; then
    echo "应用已成功启动！"
else
    echo "警告：应用启动可能失败，请检查日志"
    tail -n 20 logs/app_restart.log
fi
