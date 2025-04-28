#!/bin/bash

# 错误时停止脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 恢复默认颜色

# 配置信息
SERVER="root@47.236.39.134"
PEM_FILE="vincent.pem"
FLASK_APP_DIR="/home/vincent/RWA-HUB_4.0/app"
STATIC_DIR="${FLASK_APP_DIR}/static/js"
TEMPLATES_DIR="${FLASK_APP_DIR}/templates"
BACKUP_DIR="/home/vincent/backups/$(date +%Y%m%d_%H%M%S)"

# 本地文件路径
DIVIDEND_FIX_JS="app/static/js/dividend_fix.js"
BUY_BUTTON_FIX_JS="app/static/js/buy_button_fix.js"

# 输出函数
function info() {
  echo -e "${BLUE}[信息]${NC} $1"
}

function success() {
  echo -e "${GREEN}[成功]${NC} $1"
}

function warning() {
  echo -e "${YELLOW}[警告]${NC} $1"
}

function error() {
  echo -e "${RED}[错误]${NC} $1"
  exit 1
}

# 检查本地文件是否存在
function check_local_files() {
  info "检查本地修复文件..."
  
  local missing_files=()
  
  if [ ! -f "$DIVIDEND_FIX_JS" ]; then
    missing_files+=("$DIVIDEND_FIX_JS")
  fi
  
  if [ ! -f "$BUY_BUTTON_FIX_JS" ]; then
    missing_files+=("$BUY_BUTTON_FIX_JS")
  fi
  
  if [ ${#missing_files[@]} -ne 0 ]; then
    error "以下文件缺失:\n$(printf "  - %s\n" "${missing_files[@]}")"
  fi
  
  success "所有修复文件已就绪"
}

# 备份远程文件
function backup_remote_files() {
  info "创建服务器备份目录: $BACKUP_DIR"
  ssh -i $PEM_FILE $SERVER "mkdir -p $BACKUP_DIR"
  
  info "备份服务器文件..."
  ssh -i $PEM_FILE $SERVER "mkdir -p $BACKUP_DIR/static/js $BACKUP_DIR/templates"
  
  # 备份模板文件
  ssh -i $PEM_FILE $SERVER "cp $TEMPLATES_DIR/base.html $BACKUP_DIR/templates/ 2>/dev/null || true"
  
  success "服务器文件备份完成: $BACKUP_DIR"
}

# 从Git仓库拉取最新代码
function pull_from_git() {
  info "在服务器上从Git仓库拉取最新代码..."
  
  ssh -i $PEM_FILE $SERVER "cd /home/vincent/RWA-HUB_4.0 && git pull origin main"
  
  success "Git代码拉取完成"
}

# 验证部署
function verify_deployment() {
  info "验证部署..."
  
  # 检查JS文件是否存在
  local dividend_fix_exists=$(ssh -i $PEM_FILE $SERVER "[ -f $STATIC_DIR/dividend_fix.js ] && echo 'true' || echo 'false'")
  local buy_button_fix_exists=$(ssh -i $PEM_FILE $SERVER "[ -f $STATIC_DIR/buy_button_fix.js ] && echo 'true' || echo 'false'")
  
  if [ "$dividend_fix_exists" != "true" ]; then
    error "dividend_fix.js文件未正确部署"
  fi
  
  if [ "$buy_button_fix_exists" != "true" ]; then
    error "buy_button_fix.js文件未正确部署"
  fi
  
  # 检查base.html是否包含新的JS引用
  local dividend_ref=$(ssh -i $PEM_FILE $SERVER "grep -c 'dividend_fix.js' $TEMPLATES_DIR/base.html 2>/dev/null || echo 0")
  local buy_button_ref=$(ssh -i $PEM_FILE $SERVER "grep -c 'buy_button_fix.js' $TEMPLATES_DIR/base.html 2>/dev/null || echo 0")
  
  if [ "$dividend_ref" -eq "0" ]; then
    warning "未检测到dividend_fix.js引用，可能未正确更新base.html"
  fi
  
  if [ "$buy_button_ref" -eq "0" ]; then
    warning "未检测到buy_button_fix.js引用，可能未正确更新base.html"
  fi
  
  # 检查应用是否响应
  local http_status=$(ssh -i $PEM_FILE $SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/")
  
  if [ "$http_status" == "200" ]; then
    success "应用HTTP响应正常(状态码: 200)"
  else
    warning "应用HTTP响应异常(状态码: $http_status)"
  fi
}

# 重启应用
function restart_app() {
  info "重启Flask应用..."
  ssh -i $PEM_FILE $SERVER "cd /home/vincent/RWA-HUB_4.0 && supervisorctl restart flask_app || systemctl restart flask_app || pkill -f 'python.*run.py' || true"
  
  # 给应用一些启动时间
  sleep 5
  
  # 检查应用是否成功启动
  local is_running=$(ssh -i $PEM_FILE $SERVER "ps aux | grep -v grep | grep -c 'python.*run.py' || echo 0")
  
  if [ "$is_running" -ge "1" ]; then
    success "Flask应用已成功重启"
  else
    warning "未检测到Flask应用进程，尝试手动启动..."
    ssh -i $PEM_FILE $SERVER "cd /home/vincent/RWA-HUB_4.0 && nohup python3 run.py > flask_app.log 2>&1 &"
    sleep 3
    
    is_running=$(ssh -i $PEM_FILE $SERVER "ps aux | grep -v grep | grep -c 'python.*run.py' || echo 0")
    if [ "$is_running" -ge "1" ]; then
      success "Flask应用已手动启动"
    else
      error "无法启动Flask应用，请手动检查"
    fi
  fi
}

# 主函数
function main() {
  info "开始部署JS修复..."
  
  check_local_files
  backup_remote_files
  pull_from_git
  restart_app
  verify_deployment
  
  success "JS修复部署完成！"
}

# 执行主函数
main 