"""
安全的加密管理器
用于加密存储和解密敏感信息如私钥
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class CryptoManager:
    """安全的加密管理器"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """获取或创建主密钥"""
        # 从环境变量获取密码
        password = os.environ.get('CRYPTO_PASSWORD')
        if not password:
            raise ValueError("必须设置CRYPTO_PASSWORD环境变量作为加密密码")
        
        # 使用固定的盐值（在生产环境中应该存储在安全的地方）
        salt = b'rwa_hub_salt_2025'  # 16字节盐值
        
        # 生成密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt_private_key(self, private_key: str) -> str:
        """加密私钥"""
        try:
            encrypted_data = self.fernet.encrypt(private_key.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"私钥加密失败: {e}")
            raise
    
    def decrypt_private_key(self, encrypted_private_key: str) -> str:
        """解密私钥"""
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_private_key.encode())
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"私钥解密失败: {e}")
            raise
    
    def is_encrypted(self, data: str) -> bool:
        """检查数据是否已加密"""
        try:
            # 尝试解密，如果成功说明是加密的
            self.decrypt_private_key(data)
            return True
        except:
            return False

# 全局实例
crypto_manager = None

def get_crypto_manager() -> CryptoManager:
    """获取加密管理器实例"""
    global crypto_manager
    if crypto_manager is None:
        crypto_manager = CryptoManager()
    return crypto_manager

def encrypt_and_store_private_key(private_key: str, storage_key: str = 'SOLANA_PRIVATE_KEY_ENCRYPTED'):
    """加密并存储私钥到环境变量"""
    manager = get_crypto_manager()
    encrypted_key = manager.encrypt_private_key(private_key)
    
    # 这里应该存储到安全的配置文件或数据库中
    # 暂时打印出来让用户手动设置
    print(f"请将以下加密后的私钥设置为环境变量 {storage_key}:")
    print(encrypted_key)
    return encrypted_key

def get_decrypted_private_key(storage_key: str = 'SOLANA_PRIVATE_KEY_ENCRYPTED') -> str:
    """从环境变量获取并解密私钥"""
    encrypted_key = os.environ.get(storage_key)
    if not encrypted_key:
        raise ValueError(f"未找到加密的私钥环境变量: {storage_key}")
    
    manager = get_crypto_manager()
    return manager.decrypt_private_key(encrypted_key) 