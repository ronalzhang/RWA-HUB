#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.admin import SystemConfig
from app.utils.solana_compat.keypair import Keypair
import base58

def fix_private_key_config():
    """修复私钥配置，使其对应正确的钱包地址"""
    app = create_app()
    
    with app.app_context():
        print("🔧 修复私钥配置...")
        
        target_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
        print(f"🎯 目标钱包地址: {target_address}")
        
        # 这里需要您提供正确的私钥
        # 由于安全原因，我无法直接获取您的私钥
        print("\n❗ 重要提示:")
        print("需要您提供对应钱包地址 EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4 的私钥")
        print("请确保您有这个钱包的私钥访问权限")
        
        # 检查是否有其他可能的私钥配置
        print("\n🔍 检查其他可能的私钥配置...")
        
        # 检查所有可能的环境变量
        possible_keys = [
            'SOLANA_PRIVATE_KEY',
            'SOLANA_SERVICE_WALLET_PRIVATE_KEY',
            'PLATFORM_WALLET_PRIVATE_KEY',
            'WALLET_PRIVATE_KEY'
        ]
        
        for key_name in possible_keys:
            value = os.environ.get(key_name)
            if value:
                print(f"  {key_name}: {value[:10]}...{value[-10:]} (长度: {len(value)})")
                
                # 尝试验证这个私钥
                try:
                    private_key_bytes = base58.b58decode(value)
                    if len(private_key_bytes) == 64:
                        seed = private_key_bytes[:32]
                    elif len(private_key_bytes) == 32:
                        seed = private_key_bytes
                    else:
                        continue
                        
                    keypair = Keypair.from_seed(seed)
                    address = str(keypair.public_key)
                    print(f"    对应地址: {address}")
                    
                    if address == target_address:
                        print(f"    ✅ 找到正确的私钥！")
                        return value
                        
                except Exception as e:
                    print(f"    ❌ 私钥格式错误: {e}")
            else:
                print(f"  {key_name}: 未设置")
        
        # 检查数据库中的其他配置
        print("\n💾 检查数据库中的其他配置...")
        all_configs = SystemConfig.query.filter(
            SystemConfig.config_key.like('%private%')
        ).all()
        
        for config in all_configs:
            print(f"  {config.config_key}: {config.config_value[:10]}...{config.config_value[-10:] if len(config.config_value) > 20 else config.config_value}")
            
            # 尝试验证这个私钥
            try:
                private_key_bytes = base58.b58decode(config.config_value)
                if len(private_key_bytes) == 64:
                    seed = private_key_bytes[:32]
                elif len(private_key_bytes) == 32:
                    seed = private_key_bytes
                else:
                    continue
                    
                keypair = Keypair.from_seed(seed)
                address = str(keypair.public_key)
                print(f"    对应地址: {address}")
                
                if address == target_address:
                    print(f"    ✅ 找到正确的私钥！")
                    return config.config_value
                    
            except Exception as e:
                print(f"    ❌ 私钥格式错误: {e}")
        
        print("\n❌ 未找到对应目标地址的私钥")
        print("请检查以下可能的解决方案:")
        print("1. 确认您有钱包 EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4 的私钥")
        print("2. 将正确的私钥设置到环境变量 SOLANA_PRIVATE_KEY 中")
        print("3. 或者使用其他有私钥的钱包地址")
        
        return None

def update_private_key(correct_private_key):
    """更新私钥配置"""
    app = create_app()
    
    with app.app_context():
        print(f"\n🔄 更新私钥配置...")
        
        # 验证私钥
        try:
            private_key_bytes = base58.b58decode(correct_private_key)
            if len(private_key_bytes) == 64:
                seed = private_key_bytes[:32]
            elif len(private_key_bytes) == 32:
                seed = private_key_bytes
            else:
                print(f"❌ 私钥长度错误: {len(private_key_bytes)}")
                return False
                
            keypair = Keypair.from_seed(seed)
            address = str(keypair.public_key)
            print(f"验证地址: {address}")
            
            target_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
            if address != target_address:
                print(f"❌ 私钥不匹配目标地址")
                return False
                
        except Exception as e:
            print(f"❌ 私钥验证失败: {e}")
            return False
        
        # 更新数据库配置
        SystemConfig.set_value('SOLANA_PRIVATE_KEY', correct_private_key, '正确的Solana私钥')
        print("✅ 数据库配置已更新")
        
        # 更新环境变量文件
        env_file_path = "/root/RWA-HUB/app/.env"
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
            
            # 更新SOLANA_PRIVATE_KEY
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('SOLANA_PRIVATE_KEY='):
                    lines[i] = f'SOLANA_PRIVATE_KEY={correct_private_key}\n'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'SOLANA_PRIVATE_KEY={correct_private_key}\n')
            
            with open(env_file_path, 'w') as f:
                f.writelines(lines)
            
            print("✅ 环境变量文件已更新")
        
        return True

if __name__ == "__main__":
    result = fix_private_key_config()
    
    if result:
        print(f"\n找到正确的私钥，是否要更新配置？(y/n): ", end="")
        choice = input().strip().lower()
        if choice == 'y':
            if update_private_key(result):
                print("✅ 私钥配置修复完成！")
            else:
                print("❌ 私钥配置修复失败！")
    else:
        print("\n请手动提供正确的私钥来修复配置") 