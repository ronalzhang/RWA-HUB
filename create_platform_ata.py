#!/usr/bin/env python3
"""
创建平台USDC ATA账户的脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.config_manager import ConfigManager
from app.utils.crypto_manager import get_crypto_manager
from spl.token.instructions import get_associated_token_address, create_associated_token_account
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import Transaction
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
import time

def get_decrypted_private_key_from_db(storage_key: str = 'SOLANA_PRIVATE_KEY_ENCRYPTED') -> str:
    """从数据库获取并解密私钥，使用数据库中存储的加密参数"""
    import os
    from app.models.admin import SystemConfig
    
    print("🔐 开始从数据库解密私钥...")
    
    # 从数据库获取加密的私钥
    encrypted_key = SystemConfig.get_value(storage_key)
    if not encrypted_key:
        raise ValueError(f"未找到数据库中的加密私钥: {storage_key}")
    
    print(f"📦 获取到加密私钥: {encrypted_key[:50]}...")
    
    # 设置正确的加密参数到环境变量（临时）
    original_password = os.environ.get('CRYPTO_PASSWORD')
    original_salt = os.environ.get('CRYPTO_SALT')
    
    try:
        # 使用您提供的正确加密参数
        os.environ['CRYPTO_PASSWORD'] = 'zl4LEj1KDLxMPvwyKx5F9roBmuH73Nvqa4IcUkioBgi0HgqF4OWUCc3bfAz8uwzL'
        os.environ['CRYPTO_SALT'] = '11fd282e5a9d492ca7b4b12ce35be87d3bdd4d46038b2430645a61331a854687'
        
        print("🔑 使用正确的加密参数进行解密...")
        
        # 使用加密管理器解密
        manager = get_crypto_manager()
        decrypted_key = manager.decrypt_private_key(encrypted_key)
        
        print("✅ 私钥解密成功!")
        return decrypted_key
        
    finally:
        # 恢复原始环境变量
        if original_password:
            os.environ['CRYPTO_PASSWORD'] = original_password
        else:
            os.environ.pop('CRYPTO_PASSWORD', None)
            
        if original_salt:
            os.environ['CRYPTO_SALT'] = original_salt
        else:
            os.environ.pop('CRYPTO_SALT', None)

def create_platform_ata():
    """创建平台USDC ATA账户"""
    print("🚀 开始创建平台USDC ATA账户...")
    
    app = create_app()
    with app.app_context():
        try:
            # 1. 获取平台配置
            platform_address_str = ConfigManager.get_config('PLATFORM_FEE_ADDRESS')
            if not platform_address_str:
                print("❌ 未找到平台收款地址配置")
                return False
                
            print(f"📍 平台收款地址: {platform_address_str}")
            
            # 2. 获取并解密私钥
            try:
                private_key_str = get_decrypted_private_key_from_db('SOLANA_PRIVATE_KEY_ENCRYPTED')
                
                # Solana私钥通常是Base58格式，不是十六进制
                # 尝试直接使用Keypair.from_base58_string()解析
                try:
                    platform_keypair = Keypair.from_base58_string(private_key_str)
                    print(f"✅ 私钥解析成功（Base58格式），公钥: {platform_keypair.pubkey()}")
                except:
                    # 如果Base58失败，尝试十六进制格式
                    try:
                        private_key_bytes = bytes.fromhex(private_key_str)
                        platform_keypair = Keypair.from_bytes(private_key_bytes)
                        print(f"✅ 私钥解析成功（十六进制格式），公钥: {platform_keypair.pubkey()}")
                    except:
                        # 如果都失败，可能是其他格式，直接作为字符串使用
                        print(f"⚠️ 私钥格式未知，长度: {len(private_key_str)}, 前10字符: {private_key_str[:10]}")
                        raise Exception("无法解析私钥格式")
                
                # 验证公钥匹配
                if str(platform_keypair.pubkey()) != platform_address_str:
                    print(f"❌ 私钥公钥不匹配!")
                    print(f"   私钥对应公钥: {platform_keypair.pubkey()}")
                    print(f"   配置的地址: {platform_address_str}")
                    return False
                    
            except Exception as e:
                print(f"❌ 私钥解密失败: {e}")
                return False
            
            # 3. 计算USDC ATA地址
            platform_pubkey = Pubkey.from_string(platform_address_str)
            usdc_mint = Pubkey.from_string('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
            ata_address = get_associated_token_address(owner=platform_pubkey, mint=usdc_mint)
            
            print(f"💰 计算的USDC ATA地址: {ata_address}")
            
            # 4. 连接到Solana网络
            rpc_url = 'https://mainnet.helius-rpc.com/?api-key=edbb3e74-772d-4c65-a430-5c89f7ad02ea'
            client = Client(rpc_url, commitment=Confirmed)
            
            # 5. 检查ATA是否已存在
            ata_info = client.get_account_info(ata_address)
            if ata_info.value is not None:
                print("✅ 平台USDC ATA账户已存在，无需创建")
                return True
            
            print("🔧 ATA账户不存在，开始创建...")
            
            # 6. 创建ATA指令
            create_ata_instruction = create_associated_token_account(
                payer=platform_keypair.pubkey(),
                owner=platform_keypair.pubkey(), 
                mint=usdc_mint
            )
            
            # 7. 构建和发送交易
            recent_blockhash = client.get_latest_blockhash().value.blockhash
            transaction = Transaction(
                recent_blockhash=recent_blockhash,
                fee_payer=platform_keypair.pubkey()
            )
            transaction.add(create_ata_instruction)
            
            # 8. 签名交易
            transaction.sign(platform_keypair)
            
            # 9. 发送交易
            print("📡 发送创建ATA交易到区块链...")
            signature = client.send_transaction(
                transaction,
                opts={'skip_preflight': False, 'preflight_commitment': Confirmed}
            )
            
            print(f"✅ 交易已提交，签名: {signature.value}")
            
            # 10. 等待确认
            print("⏳ 等待交易确认...")
            for i in range(30):
                time.sleep(2)
                status = client.get_signature_status(signature.value)
                if status.value and status.value[0]:
                    if status.value[0].confirmation_status == 'confirmed':
                        print("✅ 交易已确认!")
                        break
                    elif status.value[0].err:
                        print(f"❌ 交易失败: {status.value[0].err}")
                        return False
                print(f"   第 {i+1}/30 次检查...")
            else:
                print("⏰ 交易确认超时，但可能已成功")
            
            # 11. 最终验证
            ata_info_final = client.get_account_info(ata_address)
            if ata_info_final.value is not None:
                print("🎉 平台USDC ATA账户创建成功!")
                print(f"📍 ATA地址: {ata_address}")
                print(f"🔗 交易签名: {signature.value}")
                return True
            else:
                print("❌ ATA创建可能失败，请检查区块链状态")
                return False
                
        except Exception as e:
            print(f"❌ 创建过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = create_platform_ata()
    sys.exit(0 if success else 1)