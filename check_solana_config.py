#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.helpers import get_solana_keypair_from_env
from app.utils.solana_compat.keypair import Keypair
import base58

def check_solana_config():
    """检查Solana配置"""
    app = create_app()
    
    with app.app_context():
        print("🔍 检查Solana配置...")
        
        # 检查环境变量
        print(f"\n📋 环境变量:")
        solana_private_key = os.environ.get('SOLANA_PRIVATE_KEY')
        if solana_private_key:
            print(f"  SOLANA_PRIVATE_KEY: {solana_private_key[:10]}...{solana_private_key[-10:]} (长度: {len(solana_private_key)})")
        else:
            print(f"  SOLANA_PRIVATE_KEY: 未设置")
            
        # 检查从环境变量获取的密钥对
        print(f"\n🔑 从环境变量获取密钥对:")
        keypair_info = get_solana_keypair_from_env()
        if keypair_info:
            print(f"  私钥: {keypair_info['private_key'][:10]}...{keypair_info['private_key'][-10:]}")
            print(f"  公钥: {keypair_info['public_key']}")
        else:
            print(f"  获取失败")
            
        # 检查目标钱包地址
        target_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
        print(f"\n🎯 目标钱包地址: {target_address}")
        
        # 如果有私钥，检查是否匹配
        if keypair_info:
            current_address = keypair_info['public_key']
            print(f"当前生成的地址: {current_address}")
            
            if current_address == target_address:
                print("✅ 地址匹配！")
            else:
                print("❌ 地址不匹配！")
                print("需要更新SOLANA_PRIVATE_KEY环境变量")
                
        # 检查系统配置
        try:
            from app.models.admin import SystemConfig
            db_private_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY')
            if db_private_key:
                print(f"\n💾 数据库中的私钥: {db_private_key[:10]}...{db_private_key[-10:]} (长度: {len(db_private_key)})")
                
                # 验证数据库中的私钥
                try:
                    private_key_bytes = base58.b58decode(db_private_key)
                    if len(private_key_bytes) == 64:
                        seed = private_key_bytes[:32]
                    elif len(private_key_bytes) == 32:
                        seed = private_key_bytes
                    else:
                        print(f"❌ 数据库私钥长度错误: {len(private_key_bytes)}")
                        return
                        
                    keypair = Keypair.from_seed(seed)
                    db_address = str(keypair.public_key)
                    print(f"数据库私钥对应地址: {db_address}")
                    
                    if db_address == target_address:
                        print("✅ 数据库私钥正确！")
                    else:
                        print("❌ 数据库私钥错误！")
                        
                except Exception as e:
                    print(f"❌ 验证数据库私钥失败: {e}")
            else:
                print(f"\n💾 数据库中未找到私钥")
        except Exception as e:
            print(f"❌ 检查数据库配置失败: {e}")

if __name__ == "__main__":
    check_solana_config() 