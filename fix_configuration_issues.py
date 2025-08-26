#!/usr/bin/env python3
"""
修复配置问题脚本
1. 设置正确的Helius RPC URL
2. 设置加密私钥配置
"""

import os
import sys
from app import create_app
from app.models.admin import SystemConfig
from app.utils.crypto_manager import get_crypto_manager

def fix_configuration_issues():
    """修复配置问题"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 开始修复配置问题...")
            
            # 1. 修复 SOLANA_RPC_URL 配置
            helius_rpc_url = "https://mainnet.helius-rpc.com/?api-key=edbb3e74-772d-4c65-a430-5c89f7ad02ea"
            
            # 更新数据库配置
            SystemConfig.set_value('SOLANA_RPC_URL', helius_rpc_url, '主要Solana RPC节点(Helius)')
            print(f"✅ 已更新数据库中的SOLANA_RPC_URL配置")
            
            # 2. 设置加密私钥配置
            crypto_password = "123abc74531"  # 你设置的加密密钥
            
            # 检查是否已有私钥配置
            existing_encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
            existing_encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
            
            if not existing_encrypted_key or not existing_encrypted_password:
                print("🔐 设置加密私钥配置...")
                
                # 设置系统加密密钥
                os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
                system_crypto = get_crypto_manager()
                
                # 加密用户密码
                encrypted_password = system_crypto.encrypt_private_key(crypto_password)
                SystemConfig.set_value('CRYPTO_PASSWORD_ENCRYPTED', encrypted_password, '加密的用户密码')
                
                # 如果有私钥环境变量，也加密存储
                private_key = os.environ.get('SOLANA_PRIVATE_KEY')
                if private_key:
                    # 使用用户密码加密私钥
                    os.environ['CRYPTO_PASSWORD'] = crypto_password
                    user_crypto = get_crypto_manager()
                    encrypted_key = user_crypto.encrypt_private_key(private_key)
                    SystemConfig.set_value('SOLANA_PRIVATE_KEY_ENCRYPTED', encrypted_key, '加密的Solana私钥')
                    print("✅ 已加密并存储Solana私钥")
                else:
                    print("⚠️  未找到SOLANA_PRIVATE_KEY环境变量，跳过私钥加密")
                
                print("✅ 已设置加密密码配置")
            else:
                print("ℹ️  加密私钥配置已存在，跳过设置")
            
            # 3. 验证配置
            print("\n🔍 验证配置...")
            
            # 验证RPC URL
            updated_rpc = SystemConfig.get_value('SOLANA_RPC_URL')
            if updated_rpc == helius_rpc_url:
                print("✅ SOLANA_RPC_URL配置正确")
            else:
                print(f"❌ SOLANA_RPC_URL配置错误: {updated_rpc}")
            
            # 验证加密配置
            encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
            encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
            
            if encrypted_password:
                print("✅ 加密密码配置存在")
            else:
                print("❌ 加密密码配置缺失")
                
            if encrypted_key:
                print("✅ 加密私钥配置存在")
            else:
                print("⚠️  加密私钥配置缺失（可能需要手动设置SOLANA_PRIVATE_KEY环境变量）")
            
            print("\n✅ 配置修复完成！")
            print("📝 建议重启应用以使配置生效")
            
        except Exception as e:
            print(f"❌ 修复配置时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    success = fix_configuration_issues()
    sys.exit(0 if success else 1)