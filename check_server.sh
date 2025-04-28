#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 配置信息
SERVER="root@47.236.39.134"
PEM_FILE="vincent.pem"
FLASK_APP_DIR="/home/vincent/RWA-HUB_4.0/app"
STATIC_DIR="${FLASK_APP_DIR}/static/js"
ROUTES_DIR="${FLASK_APP_DIR}/routes"
TEMPLATES_DIR="${FLASK_APP_DIR}/templates"

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
}

# 检查文件是否在服务器上存在
function check_file_exists() {
  local file=$1
  local exists=$(ssh -i $PEM_FILE $SERVER "[ -f $file ] && echo true || echo false")
  echo $exists
}

# 检查文件内容是否包含特定字符串
function check_file_contains() {
  local file=$1
  local pattern=$2
  local result=$(ssh -i $PEM_FILE $SERVER "grep -c '$pattern' $file 2>/dev/null || echo 0")
  echo $result
}

# 检查JavaScript文件
function check_js_files() {
  info "检查JavaScript修复文件..."
  
  # 检查wallet_fix.js
  if [ "$(check_file_exists $STATIC_DIR/wallet_fix.js)" == "true" ]; then
    success "wallet_fix.js 文件存在"
    
    # 检查版本
    local version=$(ssh -i $PEM_FILE $SERVER "grep -o '版本: [0-9.]*' $STATIC_DIR/wallet_fix.js 2>/dev/null || echo '未知'")
    info "wallet_fix.js $version"
    
    # 检查在base.html中的引用
    local fix_refs=$(check_file_contains $TEMPLATES_DIR/base.html "wallet_fix.js")
    if [ "$fix_refs" -gt "0" ]; then
      success "wallet_fix.js 在base.html中被引用 ($fix_refs 次)"
    else
      error "wallet_fix.js 未在base.html中被引用"
    fi
  else
    error "wallet_fix.js 文件不存在"
  fi
  
  # 检查wallet_debug.js
  if [ "$(check_file_exists $STATIC_DIR/wallet_debug.js)" == "true" ]; then
    success "wallet_debug.js 文件存在"
    
    # 检查版本
    local version=$(ssh -i $PEM_FILE $SERVER "grep -o '版本: [0-9.]*' $STATIC_DIR/wallet_debug.js 2>/dev/null || echo '未知'")
    info "wallet_debug.js $version"
    
    # 检查在base.html中的引用
    local debug_refs=$(check_file_contains $TEMPLATES_DIR/base.html "wallet_debug.js")
    if [ "$debug_refs" -gt "0" ]; then
      success "wallet_debug.js 在base.html中被引用 ($debug_refs 次)"
    else
      warning "wallet_debug.js 未在base.html中被引用"
    fi
  else
    warning "wallet_debug.js 文件不存在"
  fi
}

# 检查API修复
function check_api_fix() {
  info "检查API修复状态..."
  
  # 检查api.py.fixed
  if [ "$(check_file_exists $ROUTES_DIR/api.py.fixed)" == "true" ]; then
    success "api.py.fixed 文件存在"
    
    # 检查api.py是否已经应用修复
    local api_size=$(ssh -i $PEM_FILE $SERVER "wc -l $ROUTES_DIR/api.py | awk '{print \$1}'")
    local api_fixed_size=$(ssh -i $PEM_FILE $SERVER "wc -l $ROUTES_DIR/api.py.fixed | awk '{print \$1}'")
    
    info "api.py: $api_size 行, api.py.fixed: $api_fixed_size 行"
    
    # 检查是否包含修复标记
    if [ "$(check_file_contains $ROUTES_DIR/api.py 'Fixed version')" -gt "0" ]; then
      success "api.py 已应用修复 (包含Fixed version标记)"
    else
      # 比较文件内容
      local diff_count=$(ssh -i $PEM_FILE $SERVER "diff $ROUTES_DIR/api.py $ROUTES_DIR/api.py.fixed | wc -l")
      if [ "$diff_count" -eq "0" ]; then
        success "api.py 已应用修复 (与api.py.fixed内容一致)"
      else
        warning "api.py 可能未应用最新修复 (与api.py.fixed有 $diff_count 行不同)"
      fi
    fi
  else
    warning "api.py.fixed 文件不存在"
  fi
}

# 检查应用运行状态
function check_app_status() {
  info "检查应用运行状态..."
  
  # 检查进程
  local process_count=$(ssh -i $PEM_FILE $SERVER "ps aux | grep -v grep | grep -c 'python.*run.py'")
  
  if [ "$process_count" -gt "0" ]; then
    success "Flask应用正在运行 ($process_count 个进程)"
    
    # 获取进程详情
    local process_details=$(ssh -i $PEM_FILE $SERVER "ps aux | grep -v grep | grep 'python.*run.py'")
    info "进程详情:\n$process_details"
  else
    error "Flask应用未运行!"
  fi
  
  # 检查HTTP响应
  local http_status=$(ssh -i $PEM_FILE $SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/")
  
  if [ "$http_status" == "200" ]; then
    success "应用HTTP响应正常 (状态码: 200)"
  else
    error "应用HTTP响应异常 (状态码: $http_status)"
  fi
  
  # 检查最近的日志
  info "最近的应用日志:"
  ssh -i $PEM_FILE $SERVER "cd /home/vincent/RWA-HUB_4.0 && tail -n 20 flask_app.log"
}

# 检查系统资源
function check_system_resources() {
  info "检查服务器资源使用情况..."
  
  # 检查CPU和内存使用
  local cpu_usage=$(ssh -i $PEM_FILE $SERVER "top -bn1 | grep 'Cpu(s)' | awk '{print \$2 + \$4}'")
  local mem_usage=$(ssh -i $PEM_FILE $SERVER "free -m | awk 'NR==2{printf \"%.2f%%\", \$3*100/\$2 }'")
  local disk_usage=$(ssh -i $PEM_FILE $SERVER "df -h / | awk 'NR==2{print \$5}'")
  
  info "CPU使用率: $cpu_usage%"
  info "内存使用率: $mem_usage"
  info "磁盘使用率: $disk_usage"
  
  # 检查系统负载
  local load=$(ssh -i $PEM_FILE $SERVER "uptime | awk -F'[a-z]:' '{print \$2}'")
  info "系统负载: $load"
  
  # 检查运行时间
  local uptime=$(ssh -i $PEM_FILE $SERVER "uptime -p")
  info "服务器运行时间: $uptime"
}

# 主函数
function main() {
  echo "===================================="
  echo "  服务器修复状态检查工具 v1.0.0"
  echo "===================================="
  
  # 测试SSH连接
  info "测试SSH连接..."
  if ssh -i $PEM_FILE -o ConnectTimeout=5 $SERVER "echo 连接成功" &>/dev/null; then
    success "成功连接到服务器"
  else
    error "无法连接到服务器，请检查SSH配置"
    exit 1
  fi
  
  # 执行检查步骤
  check_js_files
  check_api_fix
  check_app_status
  check_system_resources
  
  echo ""
  echo "===================================="
  echo -e "${GREEN}  检查完成!${NC}"
  echo "===================================="
}

# 执行主函数
main 