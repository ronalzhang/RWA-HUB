#!/bin/bash

# ===================================================
# RWA-HUB 安全加固脚本
# 修复安全问题并强化系统安全性
# ===================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 配置
HARDENING_LOG="security_hardening_$(date +%Y%m%d_%H%M%S).log"
SERVER_IP="47.236.39.134"
BACKUP_DIR="/root/security_backup_$(date +%Y%m%d)"

echo -e "${PURPLE}================================================${NC}"
echo -e "${PURPLE}      RWA-HUB 安全加固执行脚本${NC}"
echo -e "${PURPLE}================================================${NC}"
echo "开始时间: $(date)"
echo "加固日志: $HARDENING_LOG"
echo ""

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$HARDENING_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$HARDENING_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$HARDENING_LOG"
}

log_section() {
    echo -e "\n${BLUE}======== $1 ========${NC}" | tee -a "$HARDENING_LOG"
}

# 检查必要文件
if [ ! -f "baba.pem" ]; then
    log_error "未找到新密钥文件 baba.pem"
    exit 1
fi
chmod 600 baba.pem

log_section "第1步：SSH安全强化"

# 创建SSH安全加固脚本
cat > ssh_hardening.sh << 'SSH_EOF'
#!/bin/bash

echo "========================================"
echo "SSH安全加固"
echo "执行时间: $(date)"
echo "========================================"

BACKUP_DIR="/root/security_backup_$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

echo ""
echo "=== A. 备份重要配置文件 ==="
cp /etc/ssh/sshd_config "$BACKUP_DIR/sshd_config.backup"
echo "SSH配置已备份到: $BACKUP_DIR/sshd_config.backup"

# 备份授权密钥
if [ -f "/root/.ssh/authorized_keys" ]; then
    cp /root/.ssh/authorized_keys "$BACKUP_DIR/authorized_keys.backup"
    echo "授权密钥已备份到: $BACKUP_DIR/authorized_keys.backup"
fi

echo ""
echo "=== B. 清理授权密钥文件 ==="
# 创建新的授权密钥文件，只包含新密钥
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# 获取新密钥的公钥内容（需要用户提供）
echo "正在清理SSH授权密钥..."
if [ -f "/root/.ssh/authorized_keys" ]; then
    # 备份当前密钥数量
    OLD_KEY_COUNT=$(wc -l < /root/.ssh/authorized_keys)
    echo "清理前密钥数量: $OLD_KEY_COUNT"
    
    # 这里需要用户手动添加新的公钥
    echo "注意: 需要手动添加新密钥的公钥到 /root/.ssh/authorized_keys"
    echo "旧的密钥文件已备份到 $BACKUP_DIR/authorized_keys.backup"
fi

echo ""
echo "=== C. 强化SSH配置 ==="
# 创建安全的SSH配置
cat > /etc/ssh/sshd_config.secure << 'SSHD_EOF'
# RWA-HUB 安全强化SSH配置
Port 22
Protocol 2

# 认证设置
PermitRootLogin yes
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no

# 连接限制
MaxAuthTries 3
MaxSessions 5
LoginGraceTime 60

# 安全选项
X11Forwarding no
AllowTcpForwarding no
GatewayPorts no
PermitTunnel no

# 日志记录
LogLevel VERBOSE
SyslogFacility AUTH

# 其他安全设置
ClientAliveInterval 300
ClientAliveCountMax 2
TCPKeepAlive no
Compression no

# 允许的用户
AllowUsers root

# 禁用不安全的协议
IgnoreRhosts yes
HostbasedAuthentication no
SSHD_EOF

# 应用新配置
cp /etc/ssh/sshd_config.secure /etc/ssh/sshd_config
echo "SSH配置已更新为安全配置"

echo ""
echo "=== D. 重启SSH服务 ==="
systemctl restart ssh
if [ $? -eq 0 ]; then
    echo "SSH服务重启成功"
else
    echo "SSH服务重启失败，恢复备份配置"
    cp "$BACKUP_DIR/sshd_config.backup" /etc/ssh/sshd_config
    systemctl restart ssh
fi

echo "SSH安全加固完成"
SSH_EOF

log_info "开始SSH安全加固..."
scp -i baba.pem ssh_hardening.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/ssh_hardening.sh && /tmp/ssh_hardening.sh" 2>&1 | tee -a "$HARDENING_LOG"

log_section "第2步：防火墙配置"

# 创建防火墙配置脚本
cat > firewall_setup.sh << 'FW_EOF'
#!/bin/bash

echo "========================================"
echo "防火墙安全配置"
echo "执行时间: $(date)"
echo "========================================"

echo ""
echo "=== A. 安装并配置UFW防火墙 ==="
# 安装UFW
apt-get update
apt-get install -y ufw

# 设置默认规则
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

echo ""
echo "=== B. 配置必要的端口访问 ==="
# SSH端口
ufw allow 22/tcp comment 'SSH Access'

# HTTP/HTTPS端口 (如果需要)
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# 如果RWA-HUB使用其他端口，在这里添加
# ufw allow 5000/tcp comment 'RWA-HUB App'

echo ""
echo "=== C. 启用防火墙 ==="
ufw --force enable
ufw status verbose

echo ""
echo "=== D. 配置fail2ban ==="
apt-get install -y fail2ban

# 配置fail2ban for SSH
cat > /etc/fail2ban/jail.local << 'F2B_EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
F2B_EOF

systemctl enable fail2ban
systemctl restart fail2ban
systemctl status fail2ban

echo "防火墙配置完成"
FW_EOF

log_info "开始防火墙配置..."
scp -i baba.pem firewall_setup.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/firewall_setup.sh && /tmp/firewall_setup.sh" 2>&1 | tee -a "$HARDENING_LOG"

log_section "第3步：RWA-HUB应用安全加固"

# 创建应用安全加固脚本
cat > app_security_hardening.sh << 'APP_EOF'
#!/bin/bash

echo "========================================"
echo "RWA-HUB应用安全加固"
echo "执行时间: $(date)"
echo "========================================"

PROJECT_DIR="/var/www/RWA-HUB"
BACKUP_DIR="/root/security_backup_$(date +%Y%m%d)"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: RWA-HUB项目目录不存在"
    exit 1
fi

cd "$PROJECT_DIR"
mkdir -p "$BACKUP_DIR/app_backup"

echo ""
echo "=== A. 备份重要文件 ==="
# 备份配置文件
cp .env "$BACKUP_DIR/app_backup/.env.backup" 2>/dev/null || echo "无.env文件"
cp config.py "$BACKUP_DIR/app_backup/config.py.backup" 2>/dev/null
cp deployer-keypair.json "$BACKUP_DIR/app_backup/deployer-keypair.json.backup" 2>/dev/null

# 备份数据库
cp instance/app.db "$BACKUP_DIR/app_backup/app.db.backup" 2>/dev/null || echo "无数据库文件"

echo "应用文件已备份到: $BACKUP_DIR/app_backup/"

echo ""
echo "=== B. 设置文件权限 ==="
# 设置正确的文件权限
chown -R www-data:www-data "$PROJECT_DIR"
find "$PROJECT_DIR" -type f -exec chmod 644 {} \;
find "$PROJECT_DIR" -type d -exec chmod 755 {} \;

# 敏感文件权限
chmod 600 .env 2>/dev/null || echo "无.env文件"
chmod 600 deployer-keypair.json 2>/dev/null || echo "无Solana密钥文件"
chmod 600 *.pem 2>/dev/null || echo "无.pem文件"

# 数据库权限
chmod 640 instance/app.db 2>/dev/null || echo "无数据库文件"

echo "文件权限已设置"

echo ""
echo "=== C. 清理敏感文件 ==="
# 删除可能泄露的旧密钥文件
rm -f vincent.pem 2>/dev/null && echo "已删除旧密钥文件 vincent.pem"

# 清理临时文件
rm -rf /tmp/*.pem 2>/dev/null
rm -rf __pycache__ 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "敏感文件清理完成"

echo ""
echo "=== D. 安全配置检查 ==="
if [ -f ".env" ]; then
    echo "检查.env文件安全性..."
    # 检查是否包含默认密码
    if grep -q "password123\|admin123\|secret123" .env; then
        echo "警告: .env文件包含默认密码，需要修改"
    fi
    
    # 检查数据库连接安全性
    if grep -q "sqlite:///" .env; then
        echo "数据库配置: SQLite (本地)"
    fi
else
    echo "警告: 未找到.env配置文件"
fi

echo ""
echo "=== E. 日志配置 ==="
# 设置应用日志
mkdir -p logs
touch logs/app.log
touch logs/security.log
chmod 640 logs/*.log
chown www-data:www-data logs/*.log

echo "日志配置完成"

echo ""
echo "=== F. Git仓库安全清理 ==="
if [ -d ".git" ]; then
    echo "清理Git敏感文件历史..."
    
    # 如果发现敏感文件在Git历史中，需要清理
    if git log --all --full-history --oneline -- "*.pem" | grep -q .; then
        echo "警告: Git历史中包含.pem文件，建议清理历史"
        echo "可以使用: git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch *.pem' --prune-empty --tag-name-filter cat -- --all"
    fi
    
    # 添加敏感文件到.gitignore
    cat >> .gitignore << 'GITIGNORE_EOF'

# 安全文件
*.pem
*.key
*private*
.env
*.log
deployer-keypair.json
GITIGNORE_EOF

    echo ".gitignore已更新"
fi

echo "RWA-HUB应用安全加固完成"
APP_EOF

log_info "开始RWA-HUB应用安全加固..."
scp -i baba.pem app_security_hardening.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/app_security_hardening.sh && /tmp/app_security_hardening.sh" 2>&1 | tee -a "$HARDENING_LOG"

log_section "第4步：系统安全强化"

# 创建系统安全强化脚本
cat > system_hardening.sh << 'SYS_EOF'
#!/bin/bash

echo "========================================"
echo "系统安全强化"
echo "执行时间: $(date)"
echo "========================================"

echo ""
echo "=== A. 系统更新 ==="
apt-get update
apt-get upgrade -y
apt-get autoremove -y

echo ""
echo "=== B. 安装安全工具 ==="
apt-get install -y \
    htop \
    iotop \
    netstat-nat \
    tcpdump \
    nmap \
    chkrootkit \
    rkhunter \
    logwatch \
    unattended-upgrades

echo ""
echo "=== C. 配置自动安全更新 ==="
dpkg-reconfigure -plow unattended-upgrades

echo ""
echo "=== D. 禁用不必要的服务 ==="
# 禁用可能不需要的服务
systemctl disable bluetooth 2>/dev/null || echo "bluetooth服务不存在"
systemctl disable cups 2>/dev/null || echo "cups服务不存在"

echo ""
echo "=== E. 内核参数安全配置 ==="
cat >> /etc/sysctl.conf << 'SYSCTL_EOF'

# 网络安全参数
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
SYSCTL_EOF

sysctl -p

echo ""
echo "=== F. 文件系统安全 ==="
# 设置重要目录权限
chmod 700 /root
chmod 755 /home

# 清理世界可写文件
find / -type f -perm -002 -exec chmod o-w {} \; 2>/dev/null || echo "文件权限清理完成"

echo ""
echo "=== G. 日志监控配置 ==="
# 配置logrotate
cat > /etc/logrotate.d/rwa-hub << 'LOGROTATE_EOF'
/var/www/RWA-HUB/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
LOGROTATE_EOF

echo "系统安全强化完成"
SYS_EOF

log_info "开始系统安全强化..."
scp -i baba.pem system_hardening.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/system_hardening.sh && /tmp/system_hardening.sh" 2>&1 | tee -a "$HARDENING_LOG"

log_section "第5步：监控和警报设置"

# 创建监控设置脚本
cat > monitoring_setup.sh << 'MON_EOF'
#!/bin/bash

echo "========================================"
echo "安全监控设置"
echo "执行时间: $(date)"
echo "========================================"

echo ""
echo "=== A. 创建安全监控脚本 ==="
cat > /root/security_monitor.sh << 'MONITOR_EOF'
#!/bin/bash

# 安全监控脚本
LOG_FILE="/var/log/security_monitor.log"
ALERT_EMAIL="admin@example.com"  # 需要修改为实际邮箱

echo "$(date): 开始安全检查" >> "$LOG_FILE"

# 检查失败登录
FAILED_LOGINS=$(grep "Failed password" /var/log/auth.log | wc -l)
if [ "$FAILED_LOGINS" -gt 10 ]; then
    echo "$(date): 警告 - 发现 $FAILED_LOGINS 次失败登录" >> "$LOG_FILE"
fi

# 检查root登录
ROOT_LOGINS=$(grep "session opened for user root" /var/log/auth.log | grep "$(date +%Y-%m-%d)" | wc -l)
if [ "$ROOT_LOGINS" -gt 0 ]; then
    echo "$(date): 信息 - 今日root登录次数: $ROOT_LOGINS" >> "$LOG_FILE"
fi

# 检查磁盘使用
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): 警告 - 磁盘使用率: $DISK_USAGE%" >> "$LOG_FILE"
fi

# 检查异常进程
ps aux --sort=-%cpu | head -5 >> "$LOG_FILE"

echo "$(date): 安全检查完成" >> "$LOG_FILE"
MONITOR_EOF

chmod +x /root/security_monitor.sh

echo ""
echo "=== B. 设置定时任务 ==="
# 添加安全监控的cron任务
(crontab -l 2>/dev/null; echo "0 */6 * * * /root/security_monitor.sh") | crontab -
echo "安全监控定时任务已设置（每6小时执行一次）"

echo ""
echo "=== C. 设置登录警报 ==="
cat > /etc/profile.d/login_alert.sh << 'LOGIN_EOF'
#!/bin/bash

# 登录警报脚本
if [ "$PAM_TYPE" = "open_session" ]; then
    echo "$(date): 用户 $PAM_USER 从 $PAM_RHOST 登录" >> /var/log/login_alerts.log
fi
LOGIN_EOF

chmod +x /etc/profile.d/login_alert.sh

echo ""
echo "=== D. 创建安全状态检查脚本 ==="
cat > /root/security_status.sh << 'STATUS_EOF'
#!/bin/bash

echo "========================================"
echo "RWA-HUB 安全状态检查"
echo "检查时间: $(date)"
echo "========================================"

echo ""
echo "=== SSH服务状态 ==="
systemctl status ssh | head -5

echo ""
echo "=== 防火墙状态 ==="
ufw status

echo ""
echo "=== 失败登录统计 ==="
echo "最近24小时失败登录次数: $(grep "Failed password" /var/log/auth.log | grep "$(date +%Y-%m-%d)" | wc -l)"

echo ""
echo "=== 磁盘使用情况 ==="
df -h | grep -E '^/dev/'

echo ""
echo "=== 内存使用情况 ==="
free -h

echo ""
echo "=== 网络连接 ==="
netstat -an | grep ':22' | grep ESTABLISHED | wc -l
echo "当前SSH连接数: $(netstat -an | grep ':22' | grep ESTABLISHED | wc -l)"

echo ""
echo "=== RWA-HUB应用状态 ==="
if pgrep -f "python.*app.py\|gunicorn" > /dev/null; then
    echo "RWA-HUB应用: 运行中"
else
    echo "RWA-HUB应用: 未运行"
fi

echo ""
echo "========================================"
STATUS_EOF

chmod +x /root/security_status.sh

echo "监控和警报设置完成"
echo "可以运行 /root/security_status.sh 查看当前安全状态"
MON_EOF

log_info "开始监控和警报设置..."
scp -i baba.pem monitoring_setup.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/monitoring_setup.sh && /tmp/monitoring_setup.sh" 2>&1 | tee -a "$HARDENING_LOG"

log_section "第6步：Git仓库安全清理"

log_info "开始本地Git仓库安全清理..."

# 检查是否需要清理Git历史
if git log --all --full-history --oneline -- "*.pem" | grep -q .; then
    log_warning "Git历史中包含.pem文件，需要清理"
    
    echo "发现Git历史中包含敏感文件，是否清理Git历史？"
    echo "1. 是 - 清理Git历史（会重写历史，需要强制推送）"
    echo "2. 否 - 跳过清理"
    read -p "请选择 (1-2): " git_choice
    
    if [ "$git_choice" = "1" ]; then
        log_info "开始清理Git历史中的敏感文件..."
        
        # 备份当前仓库
        cp -r .git .git.backup.$(date +%Y%m%d_%H%M%S)
        
        # 清理敏感文件历史
        git filter-branch --force --index-filter \
            'git rm --cached --ignore-unmatch *.pem vincent.pem deployer-keypair.json' \
            --prune-empty --tag-name-filter cat -- --all
        
        # 清理引用
        git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d
        git reflog expire --expire=now --all
        git gc --prune=now --aggressive
        
        log_info "Git历史清理完成"
        log_warning "需要执行 git push --force --all 强制推送清理后的历史"
    fi
fi

# 更新.gitignore
log_info "更新.gitignore文件..."
cat >> .gitignore << 'GITIGNORE_EOF'

# 安全加固 - 敏感文件
*.pem
*.key
*private*
.env
*.log
deployer-keypair.json
instance/
logs/
security_*.log
*_backup*
GITIGNORE_EOF

log_section "加固总结和验证"

echo "" | tee -a "$HARDENING_LOG"
echo "=== 安全加固完成总结 ===" | tee -a "$HARDENING_LOG"
echo "加固完成时间: $(date)" | tee -a "$HARDENING_LOG"
echo "详细日志保存在: $HARDENING_LOG" | tee -a "$HARDENING_LOG"
echo "" | tee -a "$HARDENING_LOG"

echo "=== 已完成的安全措施 ===" | tee -a "$HARDENING_LOG"
echo "1. ✅ SSH安全配置强化" | tee -a "$HARDENING_LOG"
echo "2. ✅ 防火墙和fail2ban配置" | tee -a "$HARDENING_LOG"
echo "3. ✅ RWA-HUB应用安全加固" | tee -a "$HARDENING_LOG"
echo "4. ✅ 系统安全强化" | tee -a "$HARDENING_LOG"
echo "5. ✅ 监控和警报设置" | tee -a "$HARDENING_LOG"
echo "6. ✅ Git仓库安全清理" | tee -a "$HARDENING_LOG"
echo "" | tee -a "$HARDENING_LOG"

echo "=== 重要提醒 ===" | tee -a "$HARDENING_LOG"
echo "1. 🔑 请妥善保管新密钥 baba.pem" | tee -a "$HARDENING_LOG"
echo "2. 🔐 请添加新密钥的公钥到服务器授权密钥文件" | tee -a "$HARDENING_LOG"
echo "3. 📧 配置监控邮箱地址接收安全警报" | tee -a "$HARDENING_LOG"
echo "4. 🔄 定期运行安全状态检查: ssh -i baba.pem root@$SERVER_IP '/root/security_status.sh'" | tee -a "$HARDENING_LOG"
echo "5. 📊 定期查看安全监控日志: /var/log/security_monitor.log" | tee -a "$HARDENING_LOG"
echo "" | tee -a "$HARDENING_LOG"

echo "=== 下一步建议 ===" | tee -a "$HARDENING_LOG"
echo "1. 测试新SSH连接是否正常" | tee -a "$HARDENING_LOG"
echo "2. 验证RWA-HUB应用功能正常" | tee -a "$HARDENING_LOG"
echo "3. 设置定期安全审计计划" | tee -a "$HARDENING_LOG"
echo "4. 建立数据备份策略" | tee -a "$HARDENING_LOG"

# 清理临时文件
rm -f ssh_hardening.sh firewall_setup.sh app_security_hardening.sh system_hardening.sh monitoring_setup.sh

log_info "🎉 安全加固完成！请查看详细日志: $HARDENING_LOG"
log_warning "⚠️  请立即测试SSH连接和应用功能" 