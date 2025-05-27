#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.admin import SystemConfig
from app.utils.solana_compat.keypair import Keypair
import base58

def set_correct_private_key():
    """手动设置正确的私钥"""
    
    target_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
    print(f"🎯 目标钱包地址: {target_address}")
    print("请提供对应此地址的私钥（Base58格式）:")
    
    # 从用户输入获取私钥
    private_key = input("私钥: ").strip()
    
    if not private_key:
        print("❌ 私钥不能为空")
        return False
    
    # 验证私钥
    try:
        private_key_bytes = base58.b58decode(private_key)
        if len(private_key_bytes) == 64:
            seed = private_key_bytes[:32]
        elif len(private_key_bytes) == 32:
            seed = private_key_bytes
        else:
            print(f"❌ 私钥长度错误: {len(private_key_bytes)}字节，期望32或64字节")
            return False
            
        keypair = Keypair.from_seed(seed)
        generated_address = str(keypair.public_key)
        
        print(f"验证生成的地址: {generated_address}")
        
        if generated_address != target_address:
            print(f"❌ 私钥不匹配目标地址")
            print(f"期望: {target_address}")
            print(f"实际: {generated_address}")
            return False
            
        print("✅ 私钥验证成功！")
        
    except Exception as e:
        print(f"❌ 私钥验证失败: {e}")
        return False
    
    # 更新配置
    app = create_app()
    with app.app_context():
        print("\n🔄 更新配置...")
        
        # 更新数据库配置
        SystemConfig.set_value('SOLANA_PRIVATE_KEY', private_key, '正确的Solana私钥')
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
                    lines[i] = f'SOLANA_PRIVATE_KEY={private_key}\n'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'SOLANA_PRIVATE_KEY={private_key}\n')
            
            with open(env_file_path, 'w') as f:
                f.writelines(lines)
            
            print("✅ 环境变量文件已更新")
        
        print("\n✅ 私钥配置修复完成！")
        print("请重启应用以使配置生效: pm2 restart rwa-hub")
        
        return True

if __name__ == "__main__":
    set_correct_private_key() 