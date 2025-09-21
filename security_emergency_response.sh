#!/bin/bash

# ===================================================
# RWA-HUB 紧急安全响应脚本
# 用于检测密钥泄露后的系统安全状态
# ===================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志文件
SECURITY_LOG="security_check_$(date +%Y%m%d_%H%M%S).log"
SERVER_IP="47.236.39.134"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  RWA-HUB 紧急安全响应检查${NC}"
echo -e "${BLUE}=====================================${NC}"
echo "开始时间: $(date)"
echo "日志文件: $SECURITY_LOG"
echo ""

# 创建日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$SECURITY_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$SECURITY_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$SECURITY_LOG"
}

log_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}" | tee -a "$SECURITY_LOG"
}

# 第一步：SSH连接测试
log_section "第1步：SSH连接安全检查"

echo "请选择操作:"
echo "1. 测试新密钥 baba.pem 连接"
echo "2. 立即执行服务器安全检查"
echo "3. 查看本地Git仓库安全状态"
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        log_info "测试新密钥连接..."
        if [ ! -f "baba.pem" ]; then
            log_error "新密钥文件 baba.pem 不存在！"
            echo "请确保 baba.pem 文件在当前目录"
            exit 1
        fi
        
        # 设置正确权限
        chmod 600 baba.pem
        log_info "已设置密钥文件权限为 600"
        
        # 测试连接
        echo "测试SSH连接: ssh -i baba.pem root@$SERVER_IP"
        ssh -i baba.pem -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@$SERVER_IP "echo 'SSH连接成功 - $(date)'" 2>&1 | tee -a "$SECURITY_LOG"
        
        if [ $? -eq 0 ]; then
            log_info "新密钥连接成功！"
        else
            log_error "新密钥连接失败！请检查网络和密钥配置"
        fi
        ;;
        
    2)
        log_info "准备执行服务器安全检查..."
        if [ ! -f "baba.pem" ]; then
            log_error "需要 baba.pem 密钥文件才能连接服务器"
            exit 1
        fi
        
        chmod 600 baba.pem
        
        # 创建服务器端检查脚本
        cat > server_security_check.sh << 'EOF'
#!/bin/bash

echo "======== 服务器安全状态检查 ========"
echo "检查时间: $(date)"
echo "服务器: $(hostname)"
echo ""

echo "=== 1. 当前登录用户检查 ==="
who
echo ""
w
echo ""

echo "=== 2. 最近登录记录 ==="
last -n 20
echo ""

echo "=== 3. SSH认证日志 (最近50行) ==="
tail -50 /var/log/auth.log | grep ssh
echo ""

echo "=== 4. 检查异常进程 ==="
ps aux --sort=-%cpu | head -10
echo ""

echo "=== 5. 网络连接检查 ==="
netstat -tulpn | grep LISTEN
echo ""

echo "=== 6. 检查cron任务 ==="
crontab -l
echo ""
ls -la /etc/cron.d/
echo ""

echo "=== 7. 检查系统用户 ==="
awk -F: '$3 >= 1000 {print $1 ":" $3 ":" $7}' /etc/passwd
echo ""

echo "=== 8. 检查sudo权限 ==="
grep -v '^#' /etc/sudoers | grep -v '^$'
echo ""

echo "=== 9. 检查SSH配置 ==="
grep -E '^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|AuthorizedKeysFile)' /etc/ssh/sshd_config
echo ""

echo "=== 10. 磁盘使用情况 ==="
df -h
echo ""

echo "=== 11. 检查RWA-HUB项目目录 ==="
if [ -d "/var/www/RWA-HUB" ]; then
    ls -la /var/www/RWA-HUB/
    echo ""
    echo "最近修改的文件:"
    find /var/www/RWA-HUB -type f -mtime -7 -ls | head -20
fi
echo ""

echo "检查完成: $(date)"
EOF

        # 上传并执行检查脚本
        scp -i baba.pem server_security_check.sh root@$SERVER_IP:/tmp/
        ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/server_security_check.sh && /tmp/server_security_check.sh" 2>&1 | tee -a "$SECURITY_LOG"
        
        log_info "服务器安全检查完成，结果已保存到 $SECURITY_LOG"
        ;;
        
    3)
        log_section "第3步：本地Git仓库安全检查"
        
        # 检查Git历史中的敏感文件
        log_info "检查Git历史中的敏感文件..."
        
        echo "=== 检查.pem文件的提交历史 ===" >> "$SECURITY_LOG"
        git log --all --full-history -- "*.pem" >> "$SECURITY_LOG" 2>&1
        
        echo "=== 检查私钥文件的提交历史 ===" >> "$SECURITY_LOG"  
        git log --all --full-history -- "*private*" "*key*" "*.json" | grep -A5 -B5 -i key >> "$SECURITY_LOG" 2>&1
        
        echo "=== 检查.env文件的提交历史 ===" >> "$SECURITY_LOG"
        git log --all --full-history -- "*.env*" >> "$SECURITY_LOG" 2>&1
        
        echo "=== 当前工作目录中的敏感文件 ===" >> "$SECURITY_LOG"
        find . -name "*.pem" -o -name "*.key" -o -name "*private*" -o -name "*.env*" | tee -a "$SECURITY_LOG"
        
        log_warning "请检查 $SECURITY_LOG 中的Git历史记录"
        log_warning "如果发现敏感文件被提交，需要清理Git历史"
        ;;
esac

echo ""
log_section "紧急响应建议"
echo "1. 如果发现异常活动，立即备份重要数据"
echo "2. 检查RWA-HUB应用的配置文件是否被修改"
echo "3. 验证数据库数据完整性"
echo "4. 确认没有新增的管理员账户"
echo "5. 运行完整的安全审计脚本: ./security_full_audit.sh"

echo ""
echo "下一步请运行: ./security_full_audit.sh 进行深度安全检查"
echo "日志文件: $SECURITY_LOG" 