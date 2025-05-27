#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.admin import SystemConfig
from app.utils.solana_compat.keypair import Keypair
import base58

def verify_user_private_key():
    """验证用户提供的私钥并诊断配置问题"""
    
    # 用户提供的私钥
    user_private_key = "4btSt2bvXDjv9Ae1egayTvXkdk9LzocRkbVrjdwi1AFhD8HMcka8SqApydDedDiQdZNkh2BU4bd2DtsdV35dFuRN"
    user_crypto_password = "123abc$74531ABC"
    target_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
    
    print("🔍 验证用户提供的私钥...")
    print(f"🎯 目标钱包地址: {target_address}")
    print(f"🔑 用户提供的私钥: {user_private_key[:10]}...{user_private_key[-10:]}")
    print(f"🔐 用户提供的密码: {user_crypto_password}")
    
    # 1. 验证私钥是否对应目标地址
    print(f"\n📋 步骤1: 验证私钥...")
    try:
        private_key_bytes = base58.b58decode(user_private_key)
        if len(private_key_bytes) == 64:
            seed = private_key_bytes[:32]
        elif len(private_key_bytes) == 32:
            seed = private_key_bytes
        else:
            print(f"❌ 私钥长度错误: {len(private_key_bytes)}字节")
            return False
            
        keypair = Keypair.from_seed(seed)
        generated_address = str(keypair.public_key)
        
        print(f"生成的地址: {generated_address}")
        
        if generated_address == target_address:
            print("✅ 私钥验证成功！地址匹配")
        else:
            print("❌ 私钥验证失败！地址不匹配")
            print(f"期望: {target_address}")
            print(f"实际: {generated_address}")
            return False
            
    except Exception as e:
        print(f"❌ 私钥验证失败: {e}")
        return False
    
    # 2. 检查数据库配置
    app = create_app()
    with app.app_context():
        print(f"\n📋 步骤2: 检查数据库配置...")
        
        # 检查加密私钥
        encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
        if encrypted_key:
            print(f"✅ 找到加密私钥: {encrypted_key[:20]}...{encrypted_key[-20:]}")
        else:
            print("❌ 数据库中未找到加密私钥")
        
        # 检查加密密码
        encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
        if encrypted_password:
            print(f"✅ 找到加密密码: {encrypted_password[:20]}...{encrypted_password[-20:]}")
        else:
            print("❌ 数据库中未找到加密密码")
        
        # 检查明文私钥
        plain_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY')
        if plain_key:
            print(f"⚠️  找到明文私钥: {plain_key[:10]}...{plain_key[-10:]}")
        else:
            print("ℹ️  数据库中未找到明文私钥")
    
    # 3. 测试解密过程
    print(f"\n📋 步骤3: 测试解密过程...")
    if encrypted_key and encrypted_password:
        try:
            # 设置环境变量
            original_password = os.environ.get('CRYPTO_PASSWORD')
            
            # 先用系统密钥解密用户密码
            os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
            
            from app.utils.crypto_manager import get_crypto_manager
            system_crypto = get_crypto_manager()
            decrypted_user_password = system_crypto.decrypt_private_key(encrypted_password)
            
            print(f"解密出的用户密码: {decrypted_user_password}")
            
            if decrypted_user_password == user_crypto_password:
                print("✅ 用户密码匹配！")
                
                # 用用户密码解密私钥
                os.environ['CRYPTO_PASSWORD'] = decrypted_user_password
                user_crypto = get_crypto_manager()
                decrypted_private_key = user_crypto.decrypt_private_key(encrypted_key)
                
                print(f"解密出的私钥: {decrypted_private_key[:10]}...{decrypted_private_key[-10:]}")
                
                if decrypted_private_key == user_private_key:
                    print("✅ 私钥解密成功！完全匹配")
                else:
                    print("❌ 私钥解密后不匹配")
                    print(f"期望: {user_private_key}")
                    print(f"实际: {decrypted_private_key}")
                    
            else:
                print("❌ 用户密码不匹配")
                print(f"期望: {user_crypto_password}")
                print(f"实际: {decrypted_user_password}")
            
            # 恢复原始密码
            if original_password:
                os.environ['CRYPTO_PASSWORD'] = original_password
            elif 'CRYPTO_PASSWORD' in os.environ:
                del os.environ['CRYPTO_PASSWORD']
                
        except Exception as e:
            print(f"❌ 解密测试失败: {e}")
    
    # 4. 检查环境变量
    print(f"\n📋 步骤4: 检查环境变量...")
    env_private_key = os.environ.get('SOLANA_PRIVATE_KEY')
    if env_private_key:
        print(f"⚠️  环境变量SOLANA_PRIVATE_KEY: {env_private_key[:10]}...{env_private_key[-10:]}")
        
        # 验证这个环境变量私钥
        try:
            private_key_bytes = base58.b58decode(env_private_key)
            if len(private_key_bytes) == 64:
                seed = private_key_bytes[:32]
            elif len(private_key_bytes) == 32:
                seed = private_key_bytes
            else:
                print(f"❌ 环境变量私钥长度错误")
                return False
                
            keypair = Keypair.from_seed(seed)
            env_address = str(keypair.public_key)
            print(f"环境变量私钥对应地址: {env_address}")
            
            if env_address == target_address:
                print("✅ 环境变量私钥正确")
            else:
                print("❌ 环境变量私钥错误！这就是错误私钥的来源！")
                
        except Exception as e:
            print(f"❌ 环境变量私钥验证失败: {e}")
    else:
        print("ℹ️  环境变量SOLANA_PRIVATE_KEY未设置")
    
    # 5. 检查.env文件
    print(f"\n📋 步骤5: 检查.env文件...")
    env_file_path = "/root/RWA-HUB/app/.env"
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            if line.startswith('SOLANA_PRIVATE_KEY='):
                file_key = line.split('=', 1)[1].strip()
                print(f"⚠️  .env文件中的私钥: {file_key[:10]}...{file_key[-10:]}")
                
                if file_key == user_private_key:
                    print("✅ .env文件中的私钥正确")
                else:
                    print("❌ .env文件中的私钥错误！")
                break
        else:
            print("ℹ️  .env文件中未找到SOLANA_PRIVATE_KEY")
    else:
        print("❌ .env文件不存在")
    
    return True

def fix_configuration():
    """修复配置"""
    user_private_key = "4btSt2bvXDjv9Ae1egayTvXkdk9LzocRkbVrjdwi1AFhD8HMcka8SqApydDedDiQdZNkh2BU4bd2DtsdV35dFuRN"
    user_crypto_password = "123abc$74531ABC"
    
    app = create_app()
    with app.app_context():
        print(f"\n🔧 修复配置...")
        
        # 1. 设置正确的环境变量
        os.environ['CRYPTO_PASSWORD'] = user_crypto_password
        print("✅ 设置CRYPTO_PASSWORD环境变量")
        
        # 2. 更新.env文件
        env_file_path = "/root/RWA-HUB/app/.env"
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
            
            # 更新SOLANA_PRIVATE_KEY
            updated_solana = False
            updated_crypto = False
            
            for i, line in enumerate(lines):
                if line.startswith('SOLANA_PRIVATE_KEY='):
                    lines[i] = f'SOLANA_PRIVATE_KEY={user_private_key}\n'
                    updated_solana = True
                elif line.startswith('CRYPTO_PASSWORD='):
                    lines[i] = f'CRYPTO_PASSWORD={user_crypto_password}\n'
                    updated_crypto = True
            
            if not updated_solana:
                lines.append(f'SOLANA_PRIVATE_KEY={user_private_key}\n')
            if not updated_crypto:
                lines.append(f'CRYPTO_PASSWORD={user_crypto_password}\n')
            
            with open(env_file_path, 'w') as f:
                f.writelines(lines)
            
            print("✅ 更新.env文件")
        
        # 3. 更新数据库配置
        SystemConfig.set_value('SOLANA_PRIVATE_KEY', user_private_key, '正确的Solana私钥')
        print("✅ 更新数据库明文私钥")
        
        print("\n✅ 配置修复完成！")
        print("请重启应用: pm2 restart rwa-hub")

if __name__ == "__main__":
    if verify_user_private_key():
        print(f"\n是否要修复配置？(y/n): ", end="")
        choice = input().strip().lower()
        if choice == 'y':
            fix_configuration()
    else:
        print("❌ 私钥验证失败，无法修复配置") 