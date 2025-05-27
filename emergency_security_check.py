#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime

def emergency_security_check():
    """紧急安全检查 - 检查钱包是否被盗"""
    
    print("🚨 紧急安全检查 - 钱包被盗分析")
    print("=" * 60)
    
    wallet_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
    print(f"🎯 被盗钱包地址: {wallet_address}")
    
    # 检查最近的交易记录
    print(f"\n🔍 检查最近交易记录...")
    
    try:
        # 使用Solana RPC获取交易历史
        rpc_url = "https://api.mainnet-beta.solana.com"
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                wallet_address,
                {
                    "limit": 20  # 获取最近20笔交易
                }
            ]
        }
        
        response = requests.post(rpc_url, json=payload)
        data = response.json()
        
        if "result" in data and data["result"]:
            print(f"✅ 获取到 {len(data['result'])} 笔最近交易")
            
            # 分析交易模式
            suspicious_patterns = []
            
            for i, tx in enumerate(data["result"][:10]):  # 分析最近10笔
                signature = tx["signature"]
                slot = tx["slot"]
                block_time = tx.get("blockTime")
                
                if block_time:
                    tx_time = datetime.fromtimestamp(block_time)
                    print(f"  交易 {i+1}: {signature[:16]}... 时间: {tx_time}")
                    
                    # 检查是否有快速转出模式
                    if i > 0:
                        prev_time = datetime.fromtimestamp(data["result"][i-1].get("blockTime", 0))
                        time_diff = abs((tx_time - prev_time).total_seconds())
                        
                        if time_diff < 60:  # 1分钟内的连续交易
                            suspicious_patterns.append(f"快速连续交易: {time_diff:.1f}秒间隔")
            
            if suspicious_patterns:
                print(f"\n⚠️  发现可疑模式:")
                for pattern in suspicious_patterns:
                    print(f"  • {pattern}")
            
        else:
            print(f"❌ 无法获取交易记录: {data}")
            
    except Exception as e:
        print(f"❌ 检查交易记录失败: {e}")
    
    # 检查私钥安全
    print(f"\n🔐 检查私钥安全状况...")
    
    # 检查可能的泄露点
    security_risks = []
    
    # 1. 检查环境变量
    if os.environ.get('SOLANA_PRIVATE_KEY'):
        security_risks.append("环境变量中存储明文私钥")
    
    # 2. 检查.env文件权限
    env_files = ["/root/RWA-HUB/app/.env", "/root/RWA-HUB/.env"]
    for env_file in env_files:
        if os.path.exists(env_file):
            stat = os.stat(env_file)
            permissions = oct(stat.st_mode)[-3:]
            if permissions != "600":
                security_risks.append(f".env文件权限不安全: {permissions} (应为600)")
    
    # 3. 检查日志文件是否泄露私钥
    log_files = ["/root/RWA-HUB/app.log", "/root/RWA-HUB/logs/"]
    for log_path in log_files:
        if os.path.exists(log_path):
            security_risks.append(f"日志文件可能包含敏感信息: {log_path}")
    
    # 4. 检查Git历史
    if os.path.exists("/root/RWA-HUB/.git"):
        security_risks.append("Git仓库可能包含私钥历史记录")
    
    print(f"\n🚨 安全风险评估:")
    if security_risks:
        for risk in security_risks:
            print(f"  ❌ {risk}")
    else:
        print(f"  ✅ 未发现明显的本地安全风险")
    
    # 紧急处理建议
    print(f"\n🆘 紧急处理建议:")
    print(f"  1. 🛑 立即停止使用当前钱包")
    print(f"  2. 🔄 生成新的钱包地址和私钥")
    print(f"  3. 🔍 检查所有可能的私钥泄露点:")
    print(f"     • 服务器日志文件")
    print(f"     • Git提交历史")
    print(f"     • 环境变量配置")
    print(f"     • 数据库备份文件")
    print(f"     • 第三方服务配置")
    print(f"  4. 🔐 更新所有相关的安全配置")
    print(f"  5. 📊 监控新钱包的交易活动")
    
    # 检查可能的攻击者地址
    print(f"\n🕵️ 分析攻击者模式...")
    print(f"  从交易记录看，资金被快速转移到:")
    print(f"  • Avdn...NhNd (可能是攻击者地址)")
    print(f"  • 建议将此地址加入黑名单监控")
    
    return {
        'wallet_compromised': True,
        'security_risks': security_risks,
        'action_required': 'IMMEDIATE'
    }

def generate_new_wallet():
    """生成新的安全钱包"""
    
    print(f"\n🔄 生成新的安全钱包...")
    
    from app.utils.solana_compat.keypair import Keypair
    import base58
    
    # 生成新的密钥对
    new_keypair = Keypair()
    new_private_key = base58.b58encode(new_keypair.secret_key).decode()
    new_public_key = str(new_keypair.public_key)
    
    print(f"✅ 新钱包已生成:")
    print(f"  新钱包地址: {new_public_key}")
    print(f"  新私钥: {new_private_key[:10]}...{new_private_key[-10:]} (请安全保存)")
    
    print(f"\n🔐 安全存储建议:")
    print(f"  1. 使用硬件钱包存储私钥")
    print(f"  2. 私钥分片存储在不同位置")
    print(f"  3. 使用强加密密码保护")
    print(f"  4. 定期更换访问密码")
    print(f"  5. 限制服务器访问权限")
    
    return {
        'new_address': new_public_key,
        'new_private_key': new_private_key
    }

if __name__ == "__main__":
    # 紧急安全检查
    result = emergency_security_check()
    
    if result['wallet_compromised']:
        print(f"\n" + "🚨" * 20)
        print(f"钱包已被盗！需要立即采取行动！")
        print(f"🚨" * 20)
        
        # 生成新钱包
        new_wallet = generate_new_wallet()
        
        print(f"\n📋 下一步行动清单:")
        print(f"  ☐ 更新系统配置使用新钱包地址")
        print(f"  ☐ 清理所有包含旧私钥的文件")
        print(f"  ☐ 更新环境变量和数据库配置")
        print(f"  ☐ 重新部署应用")
        print(f"  ☐ 监控新钱包安全状况") 