#!/usr/bin/env python3
"""
修复自动上链系统
"""

import os
import secrets
import base58
from app import create_app
from app.models.admin import SystemConfig
from app.utils.solana_compat.keypair import Keypair

def fix_auto_onchain_system():
    app = create_app()
    with app.app_context():
        print('=== 修复自动上链系统 ===\\n')
        
        # 检查当前配置
        current_plain_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY')
        encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
        
        print(f'当前明文私钥: {current_plain_key}')
        print(f'加密私钥长度: {len(encrypted_key) if encrypted_key else "None"}')
        
        # 生成新的Solana私钥
        print('\\n=== 生成新的Solana私钥 ===')
        try:
            # 生成32字节的随机种子
            seed = secrets.token_bytes(32)
            
            # 使用兼容库创建密钥对
            keypair = Keypair.from_seed(seed)
            
            # 转换为base58格式
            private_key_b58 = base58.b58encode(keypair.secret_key).decode()
            public_key_b58 = str(keypair.public_key)
            
            print(f'✓ 新生成的私钥长度: {len(private_key_b58)}')
            print(f'✓ 对应的公钥: {public_key_b58}')
            
            # 保存到数据库
            SystemConfig.set_value('SOLANA_PRIVATE_KEY', private_key_b58, '新生成的Solana私钥')
            print('✓ 私钥已保存到数据库')
            
            # 清除加密私钥，强制使用明文
            SystemConfig.set_value('SOLANA_PRIVATE_KEY_ENCRYPTED', '', '清除无效的加密私钥')
            print('✓ 已清除无效的加密私钥')
            
            # 设置环境变量
            env_file_path = "/root/RWA-HUB/app/.env"
            
            # 读取现有文件
            lines = []
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r') as f:
                    lines = f.readlines()
            
            # 更新或添加SOLANA_PRIVATE_KEY
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('SOLANA_PRIVATE_KEY='):
                    lines[i] = f'SOLANA_PRIVATE_KEY={private_key_b58}\\n'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'SOLANA_PRIVATE_KEY={private_key_b58}\\n')
            
            # 写回文件
            with open(env_file_path, 'w') as f:
                f.writelines(lines)
            
            print('✓ 环境变量已更新')
            
            # 清理上链处理状态
            print('\\n=== 清理上链处理状态 ===')
            from app.models.asset import Asset
            from app.extensions import db
            
            # 重置所有"上链进行中"的资产状态
            assets_in_progress = Asset.query.filter_by(onchain_in_progress=True).all()
            for asset in assets_in_progress:
                asset.onchain_in_progress = False
                print(f'✓ 重置资产 {asset.id} 的上链状态')
            
            db.session.commit()
            print(f'✓ 已重置 {len(assets_in_progress)} 个资产的上链状态')
            
            print('\\n=== 修复完成 ===')
            print('⚠️  重要提醒：')
            print(f'   新钱包地址: {public_key_b58}')
            print('   请确保向新钱包地址转入足够的SOL用于交易费用')
            print('   建议转入至少 0.1 SOL')
            print('\\n请重启应用: pm2 restart rwa-hub')
            
            return True
            
        except Exception as e:
            print(f'✗ 生成私钥失败: {e}')
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = fix_auto_onchain_system()
    if success:
        print('\\n🎉 自动上链系统修复成功！')
    else:
        print('\\n❌ 修复失败，请检查错误信息') 