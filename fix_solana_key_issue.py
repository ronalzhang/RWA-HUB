#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.admin import SystemConfig
from app.utils.crypto_manager import CryptoManager
from app.utils.solana_compat.keypair import Keypair
import base58

def fix_solana_key():
    app = create_app()
    with app.app_context():
        print('=== 修复Solana私钥问题 ===\\n')
        
        # 检查当前明文私钥
        current_plain_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY')
        print(f'当前明文私钥: {current_plain_key}')
        print(f'明文私钥长度: {len(current_plain_key) if current_plain_key else "None"}')
        
        # 检查加密私钥
        encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
        print(f'加密私钥长度: {len(encrypted_key) if encrypted_key else "None"}')
        
        # 方案1：如果明文私钥存在且格式正确，直接使用
        if current_plain_key and len(current_plain_key) > 20:
            print('\\n=== 方案1：使用现有明文私钥 ===')
            try:
                # 设置环境变量
                os.environ['SOLANA_PRIVATE_KEY'] = current_plain_key
                print('✓ 已设置SOLANA_PRIVATE_KEY环境变量')
                
                # 清除加密私钥，强制使用明文
                SystemConfig.set_value('SOLANA_PRIVATE_KEY_ENCRYPTED', '', '清除无效的加密私钥')
                print('✓ 已清除无效的加密私钥')
                
                return True
                
            except Exception as e:
                print(f'✗ 方案1失败: {e}')
        
        # 方案2：生成新的私钥
        print('\\n=== 方案2：生成新的Solana私钥 ===')
        try:
            # 生成新的密钥对
            keypair = Keypair()
            private_key_bytes = keypair.secret_key
            
            # 转换为base58格式（Solana标准格式）
            private_key_b58 = base58.b58encode(private_key_bytes).decode()
            
            print(f'新生成的私钥长度: {len(private_key_b58)}')
            print(f'对应的公钥: {keypair.public_key}')
            
            # 保存到数据库和环境变量
            SystemConfig.set_value('SOLANA_PRIVATE_KEY', private_key_b58, '新生成的Solana私钥')
            os.environ['SOLANA_PRIVATE_KEY'] = private_key_b58
            
            # 清除加密私钥
            SystemConfig.set_value('SOLANA_PRIVATE_KEY_ENCRYPTED', '', '清除旧的加密私钥')
            
            print('✓ 新私钥已保存到数据库和环境变量')
            print('⚠️  请记录新的钱包地址，并确保有足够的SOL余额用于交易')
            
            return True
            
        except Exception as e:
            print(f'✗ 方案2失败: {e}')
        
        # 方案3：使用用户提供的密码重新加密现有私钥
        print('\\n=== 方案3：重新加密现有私钥 ===')
        if current_plain_key:
            try:
                # 使用用户提供的密码
                os.environ['CRYPTO_PASSWORD'] = '123abc$74531ABC'
                crypto_manager = CryptoManager()
                
                # 重新加密
                new_encrypted = crypto_manager.encrypt_private_key(current_plain_key)
                SystemConfig.set_value('SOLANA_PRIVATE_KEY_ENCRYPTED', new_encrypted, '重新加密的私钥')
                
                print('✓ 私钥已重新加密')
                
                # 测试解密
                decrypted = crypto_manager.decrypt_private_key(new_encrypted)
                if decrypted == current_plain_key:
                    print('✓ 解密测试成功')
                    return True
                else:
                    print('✗ 解密测试失败')
                    
            except Exception as e:
                print(f'✗ 方案3失败: {e}')
        
        return False

def fix_solana_key_issue():
    """修复Solana私钥解码问题"""
    
    user_private_key = "4btSt2bvXDjv9Ae1egayTvXkdk9LzocRkbVrjdwi1AFhD8HMcka8SqApydDedDiQdZNkh2BU4bd2DtsdV35dFuRN"
    target_address = "EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4"
    
    print("🔧 修复Solana私钥解码问题...")
    print(f"🎯 目标钱包地址: {target_address}")
    print(f"🔑 正确的私钥: {user_private_key[:10]}...{user_private_key[-10:]}")
    
    # 验证私钥解码
    print(f"\n📋 步骤1: 分析私钥格式...")
    try:
        private_key_bytes = base58.b58decode(user_private_key)
        print(f"私钥字节长度: {len(private_key_bytes)}")
        print(f"私钥前10字节: {private_key_bytes[:10].hex()}")
        print(f"私钥后10字节: {private_key_bytes[-10:].hex()}")
        
        # 测试不同的解码方式
        print(f"\n📋 步骤2: 测试不同解码方式...")
        
        # 方式1: 直接使用完整私钥
        if len(private_key_bytes) == 64:
            print("尝试方式1: 使用完整64字节作为私钥")
            try:
                keypair1 = Keypair.from_secret_key(private_key_bytes)
                address1 = str(keypair1.public_key)
                print(f"  生成地址: {address1}")
                if address1 == target_address:
                    print("  ✅ 方式1成功！")
                    return "full_64_bytes"
            except Exception as e:
                print(f"  ❌ 方式1失败: {e}")
        
        # 方式2: 使用前32字节作为seed
        if len(private_key_bytes) >= 32:
            print("尝试方式2: 使用前32字节作为seed")
            try:
                seed = private_key_bytes[:32]
                keypair2 = Keypair.from_seed(seed)
                address2 = str(keypair2.public_key)
                print(f"  生成地址: {address2}")
                if address2 == target_address:
                    print("  ✅ 方式2成功！")
                    return "first_32_bytes"
            except Exception as e:
                print(f"  ❌ 方式2失败: {e}")
        
        # 方式3: 使用后32字节作为seed
        if len(private_key_bytes) >= 32:
            print("尝试方式3: 使用后32字节作为seed")
            try:
                seed = private_key_bytes[-32:]
                keypair3 = Keypair.from_seed(seed)
                address3 = str(keypair3.public_key)
                print(f"  生成地址: {address3}")
                if address3 == target_address:
                    print("  ✅ 方式3成功！")
                    return "last_32_bytes"
            except Exception as e:
                print(f"  ❌ 方式3失败: {e}")
        
        print("❌ 所有解码方式都失败了")
        return None
        
    except Exception as e:
        print(f"❌ 私钥解码失败: {e}")
        return None

def update_helpers_logic():
    """更新helpers.py中的私钥处理逻辑"""
    
    print(f"\n🔧 更新私钥处理逻辑...")
    
    # 读取helpers.py文件
    helpers_file = "/root/RWA-HUB/app/utils/helpers.py"
    
    with open(helpers_file, 'r') as f:
        content = f.read()
    
    # 查找需要修改的部分
    old_logic = '''        # 处理不同长度的私钥
        if len(private_key_bytes) == 64:
            # 标准64字节格式，前32字节是私钥
            seed = private_key_bytes[:32]
        elif len(private_key_bytes) == 32:
            # 仅私钥
            seed = private_key_bytes
        elif len(private_key_bytes) == 66:
            # 可能包含校验和，取前32字节作为私钥
            seed = private_key_bytes[:32]
            logger.info("检测到66字节私钥，可能包含校验和，使用前32字节")
        else:
            raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}，期望32、64或66字节")'''
    
    new_logic = '''        # 处理不同长度的私钥
        if len(private_key_bytes) == 64:
            # 标准64字节格式，直接使用完整私钥
            try:
                keypair = Keypair.from_secret_key(private_key_bytes)
                return {
                    'private_key': base58.b58encode(private_key_bytes).decode(),
                    'public_key': str(keypair.public_key),
                    'keypair': keypair
                }
            except:
                # 如果失败，尝试使用前32字节作为seed
                seed = private_key_bytes[:32]
        elif len(private_key_bytes) == 32:
            # 仅私钥
            seed = private_key_bytes
        elif len(private_key_bytes) == 66:
            # 可能包含校验和，取前32字节作为私钥
            seed = private_key_bytes[:32]
            logger.info("检测到66字节私钥，可能包含校验和，使用前32字节")
        else:
            raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}，期望32、64或66字节")'''
    
    if old_logic in content:
        content = content.replace(old_logic, new_logic)
        
        with open(helpers_file, 'w') as f:
            f.write(content)
        
        print("✅ 已更新helpers.py中的私钥处理逻辑")
        return True
    else:
        print("❌ 未找到需要更新的代码段")
        return False

if __name__ == "__main__":
    # 分析私钥格式
    result = fix_solana_key_issue()
    
    if result == "full_64_bytes":
        print(f"\n✅ 找到正确的解码方式: 使用完整64字节私钥")
        if update_helpers_logic():
            print("✅ 私钥处理逻辑已更新")
            print("请重启应用: pm2 restart rwa-hub")
        else:
            print("❌ 更新私钥处理逻辑失败")
    else:
        print(f"\n❌ 未找到正确的解码方式") 