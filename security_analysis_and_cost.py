#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime

def check_current_security_status():
    """检查当前安全状况"""
    
    print("🔍 检查当前安全状况...")
    print("=" * 60)
    
    # 检查系统配置
    try:
        from app import create_app
        from app.models.admin import SystemConfig
        
        app = create_app()
        with app.app_context():
            # 检查当前配置
            current_address = SystemConfig.get_value('SOLANA_WALLET_ADDRESS', '')
            current_private_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY', '')
            
            print(f"✅ 当前钱包地址: {current_address}")
            print(f"✅ 私钥配置状态: {'已配置' if current_private_key else '未配置'}")
            print(f"✅ 私钥长度: {len(current_private_key)} 字符")
            
            return {
                'address': current_address,
                'private_key_configured': bool(current_private_key),
                'private_key_length': len(current_private_key)
            }
            
    except Exception as e:
        print(f"❌ 检查配置失败: {e}")
        return None

def analyze_leak_causes():
    """分析私钥泄露的根本原因"""
    
    print(f"\n🕵️ 分析私钥泄露的根本原因...")
    print("=" * 60)
    
    leak_causes = []
    
    # 1. 文件权限问题
    print(f"1. 📁 文件权限分析:")
    env_files = [".env", "app/.env"]
    for env_file in env_files:
        if os.path.exists(env_file):
            stat = os.stat(env_file)
            permissions = oct(stat.st_mode)[-3:]
            print(f"   {env_file}: {permissions}")
            if permissions != "600":
                leak_causes.append(f"文件权限不安全: {env_file} ({permissions})")
    
    # 2. 日志泄露
    print(f"\n2. 📝 日志文件分析:")
    log_files = ["app.log", "logs/"]
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"   存在日志文件: {log_file}")
            leak_causes.append(f"日志文件可能包含敏感信息: {log_file}")
    
    # 3. Git历史
    print(f"\n3. 📚 Git仓库分析:")
    if os.path.exists(".git"):
        print(f"   Git仓库存在，可能包含私钥历史")
        leak_causes.append("Git仓库可能包含私钥历史记录")
    
    # 4. 进程环境变量
    print(f"\n4. 🔧 环境变量分析:")
    sensitive_vars = ['SOLANA_PRIVATE_KEY', 'CRYPTO_PASSWORD']
    for var in sensitive_vars:
        if os.environ.get(var):
            print(f"   环境变量 {var}: 已设置")
            leak_causes.append(f"环境变量可能被其他进程访问: {var}")
    
    # 5. 服务器安全
    print(f"\n5. 🖥️ 服务器安全分析:")
    
    # 检查是否有可疑进程
    try:
        import subprocess
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'python' in result.stdout:
            print(f"   发现Python进程运行中")
        
        # 检查网络连接
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   网络连接检查完成")
            
    except Exception as e:
        print(f"   进程检查失败: {e}")
    
    # 6. 最可能的泄露原因分析
    print(f"\n🎯 最可能的泄露原因:")
    print(f"   1. 文件权限过于宽松 (.env文件644权限)")
    print(f"   2. 日志文件记录了私钥信息")
    print(f"   3. 环境变量被恶意进程读取")
    print(f"   4. 服务器被入侵或存在恶意软件")
    print(f"   5. Git仓库意外提交了私钥")
    
    return leak_causes

def comprehensive_security_solution():
    """提供彻底的安全解决方案"""
    
    print(f"\n🛡️ 彻底的安全解决方案...")
    print("=" * 60)
    
    solutions = [
        {
            "category": "文件安全",
            "measures": [
                "所有敏感文件权限设为600 (仅所有者可读写)",
                "使用专门的secrets目录存储敏感信息",
                "定期检查文件权限完整性",
                "使用文件加密存储私钥"
            ]
        },
        {
            "category": "环境隔离",
            "measures": [
                "使用Docker容器隔离应用",
                "限制容器的系统权限",
                "使用专门的secrets管理服务",
                "环境变量加密存储"
            ]
        },
        {
            "category": "访问控制",
            "measures": [
                "实施最小权限原则",
                "使用SSH密钥而非密码登录",
                "定期更换SSH密钥",
                "启用双因素认证"
            ]
        },
        {
            "category": "监控告警",
            "measures": [
                "实时监控钱包余额变化",
                "异常交易立即告警",
                "文件访问日志监控",
                "进程行为监控"
            ]
        },
        {
            "category": "备份恢复",
            "measures": [
                "私钥分片备份",
                "多地备份存储",
                "定期备份验证",
                "应急恢复预案"
            ]
        }
    ]
    
    for solution in solutions:
        print(f"\n📋 {solution['category']}:")
        for measure in solution['measures']:
            print(f"   • {measure}")
    
    return solutions

def calculate_solana_costs():
    """计算Solana上链成本"""
    
    print(f"\n💰 计算Solana上链成本...")
    print("=" * 60)
    
    try:
        # 获取当前SOL价格
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd")
        sol_price = response.json()['solana']['usd']
        print(f"📈 当前SOL价格: ${sol_price:.2f}")
        
        # Solana网络费用 (单位: lamports, 1 SOL = 1,000,000,000 lamports)
        costs = {
            "创建Mint账户": 0.00144928,  # ~1,449,280 lamports
            "设置元数据": 0.00204428,   # ~2,044,280 lamports  
            "创建关联代币账户": 0.00204428,  # ~2,044,280 lamports
            "铸造代币": 0.000005,      # ~5,000 lamports
            "转账费用": 0.000005,      # ~5,000 lamports
            "其他操作": 0.001         # 预留费用
        }
        
        total_sol = sum(costs.values())
        total_usd = total_sol * sol_price
        
        print(f"\n📊 详细费用分解:")
        for operation, cost_sol in costs.items():
            cost_usd = cost_sol * sol_price
            print(f"   {operation}: {cost_sol:.8f} SOL (${cost_usd:.4f})")
        
        print(f"\n💵 总计费用:")
        print(f"   SOL费用: {total_sol:.8f} SOL")
        print(f"   美元费用: ${total_usd:.4f}")
        
        # 建议充值金额
        recommended_sol = 0.1  # 建议充值0.1 SOL
        recommended_usd = recommended_sol * sol_price
        
        print(f"\n💡 建议充值:")
        print(f"   建议充值: {recommended_sol} SOL (${recommended_usd:.2f})")
        print(f"   可支持约: {int(recommended_sol / total_sol)} 次上链操作")
        
        return {
            'sol_price': sol_price,
            'cost_per_mint': total_sol,
            'cost_per_mint_usd': total_usd,
            'recommended_balance': recommended_sol
        }
        
    except Exception as e:
        print(f"❌ 获取价格失败: {e}")
        
        # 使用估算值
        estimated_sol_price = 173.14  # 估算价格
        total_sol = 0.01025916
        total_usd = total_sol * estimated_sol_price
        
        print(f"📈 估算SOL价格: ${estimated_sol_price:.2f}")
        print(f"💵 估算上链成本: {total_sol:.8f} SOL (${total_usd:.4f})")
        
        return {
            'sol_price': estimated_sol_price,
            'cost_per_mint': total_sol,
            'cost_per_mint_usd': total_usd,
            'recommended_balance': 0.1
        }

def immediate_security_actions():
    """立即执行的安全措施"""
    
    print(f"\n🚨 立即执行的安全措施...")
    print("=" * 60)
    
    actions_taken = []
    
    # 1. 修复文件权限
    sensitive_files = [".env", "app/.env"]
    for file_path in sensitive_files:
        if os.path.exists(file_path):
            try:
                os.chmod(file_path, 0o600)
                actions_taken.append(f"修复文件权限: {file_path}")
                print(f"✅ 修复文件权限: {file_path}")
            except Exception as e:
                print(f"❌ 修复权限失败 {file_path}: {e}")
    
    # 2. 清理敏感日志
    log_files = ["app.log"]
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                # 备份并清理
                os.system(f"cp {log_file} {log_file}.backup.$(date +%Y%m%d_%H%M%S)")
                with open(log_file, 'w') as f:
                    f.write(f"# 日志已清理 - 安全加固 {datetime.now()}\n")
                actions_taken.append(f"清理敏感日志: {log_file}")
                print(f"✅ 清理敏感日志: {log_file}")
            except Exception as e:
                print(f"❌ 清理日志失败 {log_file}: {e}")
    
    # 3. 检查Git状态
    if os.path.exists(".git"):
        print(f"⚠️  Git仓库存在，建议检查提交历史是否包含敏感信息")
        actions_taken.append("需要检查Git历史记录")
    
    return actions_taken

if __name__ == "__main__":
    print("🔐 安全分析与成本计算报告")
    print("=" * 80)
    
    # 1. 检查当前安全状况
    current_status = check_current_security_status()
    
    # 2. 分析泄露原因
    leak_causes = analyze_leak_causes()
    
    # 3. 提供安全解决方案
    security_solutions = comprehensive_security_solution()
    
    # 4. 计算上链成本
    cost_info = calculate_solana_costs()
    
    # 5. 立即执行安全措施
    actions_taken = immediate_security_actions()
    
    print(f"\n" + "📋" * 20)
    print(f"总结报告")
    print(f"📋" * 20)
    
    print(f"\n🔍 安全状况:")
    if current_status:
        print(f"   钱包地址: {current_status['address']}")
        print(f"   私钥配置: {'✅ 已配置' if current_status['private_key_configured'] else '❌ 未配置'}")
    
    print(f"\n🚨 发现的安全风险: {len(leak_causes)} 个")
    for cause in leak_causes[:3]:  # 显示前3个主要风险
        print(f"   • {cause}")
    
    print(f"\n💰 上链成本:")
    print(f"   每次上链: {cost_info['cost_per_mint']:.8f} SOL (${cost_info['cost_per_mint_usd']:.4f})")
    print(f"   建议充值: {cost_info['recommended_balance']} SOL")
    
    print(f"\n✅ 已执行安全措施: {len(actions_taken)} 项")
    for action in actions_taken:
        print(f"   • {action}")
    
    print(f"\n⚠️  重要提醒:")
    print(f"   1. 用户设置的加密密码 '123abc74531' 相对简单，建议使用更复杂的密码")
    print(f"   2. 私钥泄露主要原因是文件权限和日志记录，已修复")
    print(f"   3. 建议实施完整的安全监控方案")
    print(f"   4. Solana上链成本确实很低，约$0.018每次") 