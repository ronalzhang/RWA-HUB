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
ROUTES_DIR="${FLASK_APP_DIR}/routes"
TEMPLATES_DIR="${FLASK_APP_DIR}/templates"
BACKUP_DIR="/home/vincent/backups/$(date +%Y%m%d_%H%M%S)"

# 本地文件路径
WALLET_FIX_JS="app/static/js/wallet_fix.js"
WALLET_DEBUG_JS="app/static/js/wallet_debug.js"
FIXED_RUN_PY="fixed_run.py"
API_FIXED="app/routes/api.py.fixed"

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
  
  if [ ! -f "$WALLET_FIX_JS" ]; then
    missing_files+=("$WALLET_FIX_JS")
  fi
  
  if [ ! -f "$WALLET_DEBUG_JS" ]; then
    missing_files+=("$WALLET_DEBUG_JS")
  fi
  
  if [ ! -f "$FIXED_RUN_PY" ]; then
    missing_files+=("$FIXED_RUN_PY")
  fi
  
  if [ ! -f "$API_FIXED" ]; then
    missing_files+=("$API_FIXED")
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
  ssh -i $PEM_FILE $SERVER "mkdir -p $BACKUP_DIR/static/js $BACKUP_DIR/routes $BACKUP_DIR/templates"
  
  # 备份JavaScript文件
  ssh -i $PEM_FILE $SERVER "cp $STATIC_DIR/wallet.js $BACKUP_DIR/static/js/ 2>/dev/null || true"
  ssh -i $PEM_FILE $SERVER "cp $STATIC_DIR/wallet_fix.js $BACKUP_DIR/static/js/ 2>/dev/null || true"
  
  # 备份Python文件
  ssh -i $PEM_FILE $SERVER "cp /home/vincent/RWA-HUB_4.0/run.py $BACKUP_DIR/ 2>/dev/null || true"
  
  # 备份Routes文件
  ssh -i $PEM_FILE $SERVER "cp $ROUTES_DIR/api.py $BACKUP_DIR/routes/ 2>/dev/null || true"
  
  # 备份模板文件
  ssh -i $PEM_FILE $SERVER "cp $TEMPLATES_DIR/base.html $BACKUP_DIR/templates/ 2>/dev/null || true"
  
  success "服务器文件备份完成: $BACKUP_DIR"
}

# 上传修复文件
function upload_fix_files() {
  info "上传修复文件到服务器..."
  
  # 上传JavaScript修复文件
  scp -i $PEM_FILE $WALLET_FIX_JS $SERVER:$STATIC_DIR/
  scp -i $PEM_FILE $WALLET_DEBUG_JS $SERVER:$STATIC_DIR/
  
  # 上传Python修复文件
  scp -i $PEM_FILE $FIXED_RUN_PY $SERVER:/home/vincent/RWA-HUB_4.0/
  
  # 上传API修复文件
  scp -i $PEM_FILE $API_FIXED $SERVER:$ROUTES_DIR/
  
  success "所有修复文件已上传"
}

# 确保HTML模板引用了修复脚本
function ensure_js_references() {
  info "检查并更新base.html中的JavaScript引用..."
  
  # 检查wallet_fix.js引用
  local fix_js_count=$(ssh -i $PEM_FILE $SERVER "grep -c 'wallet_fix.js' $TEMPLATES_DIR/base.html 2>/dev/null || echo 0")
  
  if [ "$fix_js_count" -eq "0" ]; then
    info "添加wallet_fix.js引用到base.html..."
    ssh -i $PEM_FILE $SERVER "sed -i '/wallet\.js/a \    <script src=\"{{ url_for(\"static\", filename=\"js/wallet_fix.js\") }}\"></script>' $TEMPLATES_DIR/base.html"
  else
    info "已检测到wallet_fix.js引用"
  fi
  
  # 检查wallet_debug.js引用
  local debug_js_count=$(ssh -i $PEM_FILE $SERVER "grep -c 'wallet_debug.js' $TEMPLATES_DIR/base.html 2>/dev/null || echo 0")
  
  if [ "$debug_js_count" -eq "0" ]; then
    info "添加wallet_debug.js引用到base.html..."
    ssh -i $PEM_FILE $SERVER "sed -i '/wallet_fix\.js/a \    <script src=\"{{ url_for(\"static\", filename=\"js/wallet_debug.js\") }}\"></script>' $TEMPLATES_DIR/base.html"
  else
    info "已检测到wallet_debug.js引用"
  fi
  
  success "base.html中的JavaScript引用已更新"
}

# 重启应用
function restart_app() {
  info "应用API修复..."
  ssh -i $PEM_FILE $SERVER "cp $ROUTES_DIR/api.py.fixed $ROUTES_DIR/api.py"
  
  info "应用运行脚本修复..."
  ssh -i $PEM_FILE $SERVER "cp /home/vincent/RWA-HUB_4.0/fixed_run.py /home/vincent/RWA-HUB_4.0/run.py"
  
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

# 验证部署
function verify_deployment() {
  info "验证部署..."
  
  # 检查JS文件是否存在
  local js_files_exist=$(ssh -i $PEM_FILE $SERVER "[ -f $STATIC_DIR/wallet_fix.js ] && [ -f $STATIC_DIR/wallet_debug.js ] && echo 'true' || echo 'false'")
  
  if [ "$js_files_exist" != "true" ]; then
    error "JavaScript修复文件未正确部署"
  fi
  
  # 检查API文件是否已修复
  local api_fixed=$(ssh -i $PEM_FILE $SERVER "grep -c 'Fixed version' $ROUTES_DIR/api.py 2>/dev/null || echo 0")
  
  if [ "$api_fixed" -eq "0" ]; then
    warning "未检测到API修复标记，可能未正确应用API修复"
  fi
  
  # 检查应用是否响应
  local http_status=$(ssh -i $PEM_FILE $SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/")
  
  if [ "$http_status" == "200" ]; then
    success "应用HTTP响应正常(状态码: 200)"
  else
    warning "应用HTTP响应异常(状态码: $http_status)"
  fi
  
  success "部署验证完成"
}

# 主函数
function main() {
  echo "=================================="
  echo "  Flask应用修复部署工具 v1.0.0"  
  echo "=================================="
  
  # 执行部署步骤
  check_local_files
  backup_remote_files
  upload_fix_files
  ensure_js_references
  restart_app
  verify_deployment
  
  echo ""
  echo "=================================="
  echo -e "${GREEN}  部署完成!${NC}"
  echo "=================================="
}

# 执行主函数
main 