#!/bin/bash

# ===================================================
# RWA-HUB 完整安全审计脚本
# 深度检查系统、应用和数据安全状态
# ===================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 配置
AUDIT_LOG="security_audit_$(date +%Y%m%d_%H%M%S).log"
SERVER_IP="47.236.39.134"
PROJECT_DIR="/var/www/RWA-HUB"

echo -e "${PURPLE}================================================${NC}"
echo -e "${PURPLE}      RWA-HUB 完整安全审计检查${NC}"
echo -e "${PURPLE}================================================${NC}"
echo "开始时间: $(date)"
echo "审计日志: $AUDIT_LOG"
echo ""

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$AUDIT_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$AUDIT_LOG"
}

log_error() {
    echo -e "${RED}[CRITICAL]${NC} $1" | tee -a "$AUDIT_LOG"
}

log_section() {
    echo -e "\n${BLUE}======== $1 ========${NC}" | tee -a "$AUDIT_LOG"
}

# 检查必要文件
if [ ! -f "baba.pem" ]; then
    log_error "未找到新密钥文件 baba.pem"
    exit 1
fi
chmod 600 baba.pem

log_section "第1部分：服务器系统安全审计"

# 创建详细的服务器审计脚本
cat > detailed_server_audit.sh << 'AUDIT_EOF'
#!/bin/bash

AUDIT_DATE=$(date +"%Y-%m-%d %H:%M:%S")
echo "========================================"
echo "详细服务器安全审计报告"
echo "审计时间: $AUDIT_DATE"
echo "========================================"

echo ""
echo "=== A. 系统基础信息 ==="
echo "主机名: $(hostname)"
echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME)"
echo "内核版本: $(uname -r)"
echo "系统启动时间: $(uptime)"
echo ""

echo "=== B. 用户和权限审计 ==="
echo "--- 当前登录用户 ---"
who
echo ""
echo "--- 最近登录记录（异常IP重点关注）---"
last -n 50 | grep -E "(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)" | head -30
echo ""
echo "--- 失败登录尝试 ---"
grep "Failed password" /var/log/auth.log | tail -20 2>/dev/null || echo "无auth.log或无失败记录"
echo ""
echo "--- 所有系统用户 ---"
cat /etc/passwd | grep -E '(/bin/bash|/bin/sh)$'
echo ""
echo "--- Sudo权限用户 ---"
grep -E '^[^#].*ALL.*ALL' /etc/sudoers 2>/dev/null || echo "无sudo配置"
echo ""

echo "=== C. SSH安全配置检查 ==="
echo "--- SSH服务状态 ---"
systemctl status ssh | head -10
echo ""
echo "--- SSH配置关键项 ---"
grep -E '^(Port|PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|AuthorizedKeysFile|MaxAuthTries)' /etc/ssh/sshd_config
echo ""
echo "--- 授权公钥文件 ---"
if [ -f "/root/.ssh/authorized_keys" ]; then
    echo "Root授权密钥数量: $(wc -l < /root/.ssh/authorized_keys)"
    echo "授权密钥内容:"
    cat /root/.ssh/authorized_keys
else
    echo "未找到root用户授权密钥文件"
fi
echo ""

echo "=== D. 进程和服务检查 ==="
echo "--- 高CPU使用进程 ---"
ps aux --sort=-%cpu | head -15
echo ""
echo "--- 网络监听端口 ---"
netstat -tulpn | grep LISTEN
echo ""
echo "--- 可疑进程检查 ---"
ps aux | grep -E '(nc|netcat|wget|curl|python.*http|php.*server)' | grep -v grep || echo "未发现可疑网络进程"
echo ""

echo "=== E. 定时任务检查 ==="
echo "--- Root用户Cron任务 ---"
crontab -l 2>/dev/null || echo "无root cron任务"
echo ""
echo "--- 系统级定时任务 ---"
ls -la /etc/cron.d/ 2>/dev/null || echo "无系统cron任务"
echo ""
echo "--- 定时任务文件内容 ---"
for cronfile in /etc/cron.d/*; do
    if [ -f "$cronfile" ]; then
        echo "文件: $cronfile"
        cat "$cronfile"
        echo ""
    fi
done
echo ""

echo "=== F. 文件系统安全检查 ==="
echo "--- 异常大文件 (>100MB) ---"
find / -type f -size +100M -ls 2>/dev/null | head -10 || echo "未找到异常大文件"
echo ""
echo "--- 最近修改的系统文件 ---"
find /etc /bin /sbin /usr/bin /usr/sbin -type f -mtime -7 -ls 2>/dev/null | head -20 || echo "无最近修改的系统文件"
echo ""
echo "--- 可疑文件权限 ---"
find / -type f \( -perm -4000 -o -perm -2000 \) -ls 2>/dev/null | head -10 || echo "无异常权限文件"
echo ""

echo "=== G. 日志文件分析 ==="
echo "--- SSH登录成功记录（最近20条）---"
grep "Accepted" /var/log/auth.log | tail -20 2>/dev/null || echo "无SSH成功登录记录"
echo ""
echo "--- 异常登录尝试 ---"
grep -E "(Invalid user|illegal user|authentication failure)" /var/log/auth.log | tail -10 2>/dev/null || echo "无异常登录尝试"
echo ""
echo "--- 系统错误日志 ---"
grep -i error /var/log/syslog | tail -10 2>/dev/null || echo "无系统错误"
echo ""

echo "========================================"
echo "服务器审计完成: $(date)"
echo "========================================"
AUDIT_EOF

# 执行服务器审计
log_info "开始执行服务器系统审计..."
scp -i baba.pem detailed_server_audit.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/detailed_server_audit.sh && /tmp/detailed_server_audit.sh" 2>&1 | tee -a "$AUDIT_LOG"

log_section "第2部分：RWA-HUB应用安全审计"

# 创建应用安全检查脚本
cat > rwa_app_audit.sh << 'APP_EOF'
#!/bin/bash

echo "========================================"
echo "RWA-HUB 应用安全审计"
echo "审计时间: $(date)"
echo "========================================"

PROJECT_DIR="/var/www/RWA-HUB"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: RWA-HUB项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

echo ""
echo "=== A. 应用目录结构检查 ==="
echo "--- 项目目录权限 ---"
ls -la "$PROJECT_DIR"
echo ""
echo "--- 关键配置文件检查 ---"
ls -la *.py *.env* *.json config.py 2>/dev/null || echo "部分配置文件不存在"
echo ""

echo "=== B. 敏感文件检查 ==="
echo "--- 环境配置文件 ---"
if [ -f ".env" ]; then
    echo ".env文件存在，检查权限:"
    ls -la .env
    echo "文件大小: $(wc -c < .env) 字节"
    echo "最后修改: $(stat -c %y .env)"
else
    echo ".env文件不存在"
fi
echo ""

echo "--- 私钥文件检查 ---"
find . -name "*.pem" -o -name "*.key" -o -name "*private*" | while read file; do
    echo "发现密钥文件: $file"
    ls -la "$file"
    echo "最后修改: $(stat -c %y "$file")"
done
echo ""

echo "--- 区块链密钥文件 ---"
if [ -f "deployer-keypair.json" ]; then
    echo "Solana密钥文件存在:"
    ls -la deployer-keypair.json
    echo "最后修改: $(stat -c %y deployer-keypair.json)"
    echo "文件大小: $(wc -c < deployer-keypair.json) 字节"
else
    echo "Solana密钥文件不存在"
fi
echo ""

echo "=== C. 数据库安全检查 ==="
echo "--- 数据库文件检查 ---"
find . -name "*.db" -o -name "*.sqlite*" | while read dbfile; do
    echo "数据库文件: $dbfile"
    ls -la "$dbfile"
    echo "最后修改: $(stat -c %y "$dbfile")"
    echo "文件大小: $(ls -lh "$dbfile" | awk '{print $5}')"
done
echo ""

echo "=== D. 上传文件目录检查 ==="
if [ -d "app/static/uploads" ]; then
    echo "--- 上传目录结构 ---"
    find app/static/uploads -type f -mtime -7 -ls 2>/dev/null | head -20
    echo ""
    echo "--- 可疑文件类型 ---"
    find app/static/uploads -type f \( -name "*.php" -o -name "*.sh" -o -name "*.py" -o -name "*.exe" \) -ls 2>/dev/null || echo "无可疑文件类型"
else
    echo "上传目录不存在"
fi
echo ""

echo "=== E. Python应用检查 ==="
echo "--- 运行中的Python进程 ---"
ps aux | grep python | grep -v grep || echo "无Python进程运行"
echo ""
echo "--- 应用依赖检查 ---"
if [ -f "requirements.txt" ]; then
    echo "requirements.txt 最后修改: $(stat -c %y requirements.txt)"
    echo "依赖数量: $(wc -l < requirements.txt) 个"
else
    echo "requirements.txt 不存在"
fi
echo ""

echo "=== F. 日志文件检查 ==="
echo "--- 应用日志 ---"
if [ -f "app.log" ]; then
    echo "应用日志最后修改: $(stat -c %y app.log)"
    echo "日志大小: $(ls -lh app.log | awk '{print $5}')"
    echo "最近错误日志:"
    tail -20 app.log | grep -i error || echo "无最近错误"
else
    echo "应用日志不存在"
fi
echo ""

echo "--- 访问日志检查 ---"
if [ -d "logs" ]; then
    ls -la logs/
    echo "最近日志文件:"
    find logs -name "*.log" -mtime -7 -ls 2>/dev/null | head -10
else
    echo "logs目录不存在"
fi
echo ""

echo "=== G. Git仓库检查 ==="
if [ -d ".git" ]; then
    echo "--- Git状态 ---"
    git status
    echo ""
    echo "--- 最近提交 ---"
    git log --oneline -10
    echo ""
    echo "--- 远程仓库 ---"
    git remote -v
else
    echo "不是Git仓库"
fi
echo ""

echo "========================================"
echo "应用审计完成: $(date)"
echo "========================================"
APP_EOF

# 执行应用审计
log_info "开始执行RWA-HUB应用审计..."
scp -i baba.pem rwa_app_audit.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/rwa_app_audit.sh && /tmp/rwa_app_audit.sh" 2>&1 | tee -a "$AUDIT_LOG"

log_section "第3部分：数据库完整性检查"

# 创建数据库检查脚本
cat > database_integrity_check.py << 'DB_EOF'
#!/usr/bin/env python3
import sqlite3
import os
import sys
from datetime import datetime, timedelta

def check_database_integrity(db_path):
    print("========================================")
    print("数据库完整性检查")
    print(f"检查时间: {datetime.now()}")
    print("========================================")
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n=== 数据库文件信息 ===")
        stat = os.stat(db_path)
        print(f"文件大小: {stat.st_size / 1024 / 1024:.2f} MB")
        print(f"最后修改: {datetime.fromtimestamp(stat.st_mtime)}")
        
        print(f"\n=== 数据库表结构 ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"表 {table_name}: {count} 条记录")
        
        print(f"\n=== 用户账户检查 ===")
        try:
            cursor.execute("SELECT id, username, email, created_at, is_admin FROM user ORDER BY created_at DESC LIMIT 20;")
            users = cursor.fetchall()
            print("最近20个用户账户:")
            for user in users:
                print(f"ID: {user[0]}, 用户名: {user[1]}, 邮箱: {user[2]}, 创建时间: {user[3]}, 管理员: {user[4]}")
        except Exception as e:
            print(f"用户表检查失败: {e}")
        
        print(f"\n=== 管理员账户审计 ===")
        try:
            cursor.execute("SELECT id, username, email, created_at FROM user WHERE is_admin = 1;")
            admins = cursor.fetchall()
            print("所有管理员账户:")
            for admin in admins:
                print(f"管理员 - ID: {admin[0]}, 用户名: {admin[1]}, 邮箱: {admin[2]}, 创建时间: {admin[3]}")
        except Exception as e:
            print(f"管理员检查失败: {e}")
        
        print(f"\n=== 资产数据检查 ===")
        try:
            cursor.execute("SELECT COUNT(*) FROM asset;")
            asset_count = cursor.fetchone()[0]
            print(f"总资产数量: {asset_count}")
            
            cursor.execute("SELECT id, name, status, created_at FROM asset ORDER BY created_at DESC LIMIT 10;")
            recent_assets = cursor.fetchall()
            print("最近10个资产:")
            for asset in recent_assets:
                print(f"资产 - ID: {asset[0]}, 名称: {asset[1]}, 状态: {asset[2]}, 创建时间: {asset[3]}")
        except Exception as e:
            print(f"资产表检查失败: {e}")
        
        print(f"\n=== 交易记录检查 ===")
        try:
            cursor.execute("SELECT COUNT(*) FROM trade;")
            trade_count = cursor.fetchone()[0]
            print(f"总交易数量: {trade_count}")
            
            cursor.execute("SELECT id, user_id, asset_id, total_price, status, created_at FROM trade ORDER BY created_at DESC LIMIT 10;")
            recent_trades = cursor.fetchall()
            print("最近10笔交易:")
            for trade in recent_trades:
                print(f"交易 - ID: {trade[0]}, 用户ID: {trade[1]}, 资产ID: {trade[2]}, 金额: {trade[3]}, 状态: {trade[4]}, 时间: {trade[5]}")
        except Exception as e:
            print(f"交易表检查失败: {e}")
        
        print(f"\n=== 异常数据检查 ===")
        # 检查最近修改的重要记录
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        try:
            cursor.execute(f"SELECT COUNT(*) FROM user WHERE created_at > '{yesterday}';")
            new_users = cursor.fetchone()[0]
            print(f"昨日新增用户: {new_users}")
            
            cursor.execute(f"SELECT COUNT(*) FROM trade WHERE created_at > '{yesterday}';")
            new_trades = cursor.fetchone()[0]
            print(f"昨日新增交易: {new_trades}")
            
            # 检查异常大额交易
            cursor.execute("SELECT id, user_id, asset_id, total_price, created_at FROM trade WHERE total_price > 10 ORDER BY total_price DESC LIMIT 5;")
            large_trades = cursor.fetchall()
            if large_trades:
                print("大额交易记录:")
                for trade in large_trades:
                    print(f"大额交易 - ID: {trade[0]}, 用户ID: {trade[1]}, 资产ID: {trade[2]}, 金额: {trade[3]} ETH, 时间: {trade[4]}")
            else:
                print("无大额交易记录")
                
        except Exception as e:
            print(f"异常数据检查失败: {e}")
        
        conn.close()
        print("\n======================================")
        print("数据库完整性检查完成")
        print("======================================")
        return True
        
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    db_path = "/var/www/RWA-HUB/instance/app.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    check_database_integrity(db_path)
DB_EOF

# 执行数据库检查
log_info "开始执行数据库完整性检查..."
scp -i baba.pem database_integrity_check.py root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "cd /var/www/RWA-HUB && python3 /tmp/database_integrity_check.py" 2>&1 | tee -a "$AUDIT_LOG"

log_section "第4部分：Git仓库安全分析"

log_info "分析本地Git仓库的安全状态..."

echo "=== Git敏感文件历史检查 ===" >> "$AUDIT_LOG"
echo "检查时间: $(date)" >> "$AUDIT_LOG"
echo "" >> "$AUDIT_LOG"

# 检查敏感文件的Git历史
echo "--- 检查.pem文件提交历史 ---" >> "$AUDIT_LOG"
git log --all --full-history --oneline -- "*.pem" >> "$AUDIT_LOG" 2>&1

echo -e "\n--- 检查密钥相关文件 ---" >> "$AUDIT_LOG"
git log --all --full-history --oneline --grep="key\|private\|secret" >> "$AUDIT_LOG" 2>&1

echo -e "\n--- 检查.env文件历史 ---" >> "$AUDIT_LOG"
git log --all --full-history --oneline -- "*.env*" >> "$AUDIT_LOG" 2>&1

echo -e "\n--- 当前敏感文件状态 ---" >> "$AUDIT_LOG"
find . -name "*.pem" -o -name "*.key" -o -name "*private*" -o -name "*.env*" -o -name "deployer-keypair.json" | tee -a "$AUDIT_LOG"

log_section "第5部分：网络安全检查"

# 创建网络安全检查脚本
cat > network_security_check.sh << 'NET_EOF'
#!/bin/bash

echo "========================================"
echo "网络安全检查"
echo "检查时间: $(date)"
echo "========================================"

echo ""
echo "=== A. 防火墙状态检查 ==="
echo "--- UFW状态 ---"
ufw status verbose 2>/dev/null || echo "UFW未安装或未启用"
echo ""
echo "--- IPTables规则 ---"
iptables -L -n 2>/dev/null || echo "无法查看iptables规则"
echo ""

echo "=== B. 开放端口检查 ==="
echo "--- 监听端口详情 ---"
netstat -tulpn | grep LISTEN
echo ""
echo "--- 对外开放端口 ---"
ss -tulpn | grep LISTEN
echo ""

echo "=== C. 网络连接检查 ==="
echo "--- 当前网络连接 ---"
netstat -an | grep ESTABLISHED | head -20
echo ""
echo "--- 异常外连检查 ---"
netstat -an | grep ':22\|:80\|:443' | grep ESTABLISHED
echo ""

echo "=== D. DNS配置检查 ==="
echo "--- DNS解析配置 ---"
cat /etc/resolv.conf
echo ""

echo "=== E. 主机文件检查 ---"
echo "--- /etc/hosts 文件 ---"
cat /etc/hosts
echo ""

echo "========================================"
echo "网络安全检查完成"
echo "========================================"
NET_EOF

# 执行网络安全检查
log_info "开始执行网络安全检查..."
scp -i baba.pem network_security_check.sh root@$SERVER_IP:/tmp/
ssh -i baba.pem root@$SERVER_IP "chmod +x /tmp/network_security_check.sh && /tmp/network_security_check.sh" 2>&1 | tee -a "$AUDIT_LOG"

log_section "审计总结和建议"

echo "" | tee -a "$AUDIT_LOG"
echo "=== 审计完成总结 ===" | tee -a "$AUDIT_LOG"
echo "审计完成时间: $(date)" | tee -a "$AUDIT_LOG"
echo "详细报告保存在: $AUDIT_LOG" | tee -a "$AUDIT_LOG"
echo "" | tee -a "$AUDIT_LOG"

echo "=== 紧急安全建议 ===" | tee -a "$AUDIT_LOG"
echo "1. 立即检查审计日志中的异常登录记录" | tee -a "$AUDIT_LOG"
echo "2. 验证管理员账户是否有未授权新增" | tee -a "$AUDIT_LOG"
echo "3. 检查大额交易记录是否异常" | tee -a "$AUDIT_LOG"
echo "4. 确认.env和密钥文件是否被篡改" | tee -a "$AUDIT_LOG"
echo "5. 运行安全加固脚本: ./security_hardening.sh" | tee -a "$AUDIT_LOG"
echo "" | tee -a "$AUDIT_LOG"

echo "=== 下一步行动 ===" | tee -a "$AUDIT_LOG"
echo "1. 仔细阅读完整审计报告: $AUDIT_LOG" | tee -a "$AUDIT_LOG"
echo "2. 如发现异常，立即执行应急响应" | tee -a "$AUDIT_LOG"
echo "3. 运行安全加固脚本进行系统强化" | tee -a "$AUDIT_LOG"
echo "4. 设置持续监控机制" | tee -a "$AUDIT_LOG"

# 清理临时文件
rm -f detailed_server_audit.sh rwa_app_audit.sh database_integrity_check.py network_security_check.sh server_security_check.sh

log_info "完整安全审计结束，详细报告: $AUDIT_LOG"
log_warning "请仔细检查审计报告中的所有异常项目" 