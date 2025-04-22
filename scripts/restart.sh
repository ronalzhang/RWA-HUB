#!/bin/bash

# 设置工作目录
cd /root/RWA-HUB

# 终止当前运行的应用
echo "停止当前应用进程..."
pkill -f "python /root/RWA-HUB/run.py" || echo "没有找到运行中的应用进程"

# 确保所有Python进程都已终止
echo "确保所有相关Python进程已终止..."
for pid in $(pgrep -f "python.*run.py"); do
    echo "终止进程 $pid..."
    kill -9 $pid
done

# 检查端口是否被占用
echo "检查端口9000是否被占用..."
if lsof -i :9000 > /dev/null; then
    echo "端口9000被占用，尝试释放..."
    pid=$(lsof -i :9000 -t)
    if [ ! -z "$pid" ]; then
        echo "终止占用端口9000的进程 $pid..."
        kill -9 $pid
    fi
fi

# 再次检查端口
if lsof -i :9000 > /dev/null; then
    echo "错误：无法释放端口9000，请手动检查并释放端口"
    exit 1
fi

# 激活Python虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 运行应用
echo "启动应用..."
nohup python run.py > logs/app_restart.log 2>&1 &

# 等待应用启动
echo "等待应用启动..."
sleep 5

# 检查应用是否成功启动
if pgrep -f "python /root/RWA-HUB/run.py" > /dev/null; then
    echo "应用已成功启动！"
    
    # 检查端口是否正确绑定
    if lsof -i :9000 > /dev/null; then
        echo "端口9000已成功绑定，应用正常运行"
    else
        echo "警告：应用似乎已启动，但端口9000未绑定，请检查日志"
        tail -n 30 logs/app_restart.log
    fi
else
    echo "警告：应用启动可能失败，请检查日志"
    tail -n 30 logs/app_restart.log
fi
