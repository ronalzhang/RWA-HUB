#!/bin/bash

# RWA-HUB 稳定启动脚本
# 用于替代直接运行 python app.py

set -e

# 配置
APP_NAME="rwa-hub"
APP_DIR="/root/RWA-HUB"
PYTHON_PATH="$APP_DIR/venv/bin/python"
APP_FILE="$APP_DIR/app.py"
LOG_FILE="$APP_DIR/app.log"
PID_FILE="$APP_DIR/app.pid"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# 检查应用是否运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# 停止应用
stop_app() {
    log "停止 $APP_NAME 应用..."
    
    if is_running; then
        local pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null || true
        
        # 等待进程结束
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        # 强制杀死进程
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
        log "应用已停止"
    else
        warn "应用未运行"
    fi
    
    # 清理其他可能的进程
    pkill -f "python.*app.py" 2>/dev/null || true
}

# 启动应用
start_app() {
    log "启动 $APP_NAME 应用..."
    
    # 检查是否已经运行
    if is_running; then
        warn "应用已在运行中"
        return 0
    fi
    
    # 检查必要文件
    if [ ! -f "$PYTHON_PATH" ]; then
        error "Python虚拟环境不存在: $PYTHON_PATH"
        return 1
    fi
    
    if [ ! -f "$APP_FILE" ]; then
        error "应用文件不存在: $APP_FILE"
        return 1
    fi
    
    # 进入应用目录
    cd "$APP_DIR"
    
    # 激活虚拟环境并启动应用
    source venv/bin/activate
    
    # 设置环境变量
    export FLASK_ENV=production
    export PYTHONPATH="$APP_DIR:$PYTHONPATH"
    
    # 启动应用（后台运行）
    nohup "$PYTHON_PATH" "$APP_FILE" > "$LOG_FILE" 2>&1 &
    local pid=$!
    
    # 保存PID
    echo "$pid" > "$PID_FILE"
    
    # 等待应用启动
    sleep 3
    
    # 检查应用是否成功启动
    if is_running; then
        log "应用启动成功，PID: $pid"
        log "日志文件: $LOG_FILE"
        
        # 测试应用响应
        if curl -s http://localhost:9000/api/health > /dev/null 2>&1; then
            log "应用健康检查通过"
        else
            warn "应用健康检查失败，请检查日志"
        fi
        
        return 0
    else
        error "应用启动失败"
        if [ -f "$LOG_FILE" ]; then
            error "最近的错误日志:"
            tail -20 "$LOG_FILE"
        fi
        return 1
    fi
}

# 重启应用
restart_app() {
    log "重启 $APP_NAME 应用..."
    stop_app
    sleep 2
    start_app
}

# 查看状态
status_app() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        log "应用正在运行，PID: $pid"
        
        # 显示进程信息
        ps -p "$pid" -o pid,ppid,cmd,etime,pcpu,pmem
        
        # 测试API
        if curl -s http://localhost:9000/api/health > /dev/null 2>&1; then
            log "API响应正常"
        else
            warn "API响应异常"
        fi
    else
        warn "应用未运行"
    fi
}

# 查看日志
logs_app() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        error "日志文件不存在: $LOG_FILE"
    fi
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            start_app
            ;;
        stop)
            stop_app
            ;;
        restart)
            restart_app
            ;;
        status)
            status_app
            ;;
        logs)
            logs_app
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs}"
            echo ""
            echo "命令说明:"
            echo "  start   - 启动应用"
            echo "  stop    - 停止应用"
            echo "  restart - 重启应用"
            echo "  status  - 查看状态"
            echo "  logs    - 查看日志"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
