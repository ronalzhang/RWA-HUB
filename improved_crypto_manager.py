"""
改进的安全加密管理器
解决当前系统的安全漏洞
"""
import os
import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class ImprovedCryptoManager:
    """改进的安全加密管理器"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """获取或创建主密钥 - 使用动态盐值"""
        # 从环境变量获取密码
        password = os.environ.get('CRYPTO_PASSWORD')
        if not password:
            raise ValueError("必须设置CRYPTO_PASSWORD环境变量作为加密密码")
        
        # 从环境变量或数据库获取盐值，而不是硬编码
        salt_hex = os.environ.get('CRYPTO_SALT')
        if salt_hex:
            salt = bytes.fromhex(salt_hex)
        else:
            # 如果没有设置盐值，生成一个新的（仅用于向后兼容）
            logger.warning("未找到CRYPTO_SALT环境变量，使用默认盐值（不安全）")
            salt = b'rwa_hub_salt_2025'  # 向后兼容
        
        # 使用更高的迭代次数提高安全性
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200000,  # 从100,000增加到200,000
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
    
    def rotate_encryption(self, old_encrypted_key: str, new_password: str, new_salt: bytes) -> str:
        """轮换加密 - 使用新密码和盐值重新加密"""
        try:
            # 先用当前配置解密
            decrypted_key = self.decrypt_private_key(old_encrypted_key)
            
            # 临时更新环境变量
            old_password = os.environ.get('CRYPTO_PASSWORD')
            old_salt = os.environ.get('CRYPTO_SALT')
            
            os.environ['CRYPTO_PASSWORD'] = new_password
            os.environ['CRYPTO_SALT'] = new_salt.hex()
            
            # 创建新的加密管理器实例
            new_manager = ImprovedCryptoManager()
            new_encrypted_key = new_manager.encrypt_private_key(decrypted_key)
            
            # 恢复原始环境变量（如果需要）
            if old_password:
                os.environ['CRYPTO_PASSWORD'] = old_password
            if old_salt:
                os.environ['CRYPTO_SALT'] = old_salt
            
            return new_encrypted_key
            
        except Exception as e:
            logger.error(f"加密轮换失败: {e}")
            raise
    
    def validate_security(self) -> dict:
        """验证当前安全配置"""
        password = os.environ.get('CRYPTO_PASSWORD', '')
        salt_hex = os.environ.get('CRYPTO_SALT', '')
        
        security_score = 0
        issues = []
        
        # 检查密码强度
        if len(password) >= 32:
            security_score += 25
        elif len(password) >= 16:
            security_score += 15
            issues.append("密码长度建议至少32字符")
        else:
            issues.append("密码过短，存在安全风险")
        
        # 检查密码复杂度
        if any(c.isupper() for c in password) and any(c.islower() for c in password):
            security_score += 10
        if any(c.isdigit() for c in password):
            security_score += 10
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            security_score += 10
        
        # 检查盐值
        if salt_hex and len(salt_hex) >= 32:
            security_score += 25
        elif salt_hex:
            security_score += 15
            issues.append("盐值长度建议至少32字节")
        else:
            issues.append("未设置自定义盐值，使用默认盐值（不安全）")
        
        # 检查是否使用默认配置
        if password.startswith('123abc'):
            security_score = 0
            issues.append("使用默认密码，存在严重安全风险")
        
        if salt_hex == 'rwa_hub_salt_2025'.encode().hex():
            security_score = 0
            issues.append("使用默认盐值，存在严重安全风险")
        
        # 安全等级
        if security_score >= 80:
            level = "高"
        elif security_score >= 60:
            level = "中"
        elif security_score >= 40:
            level = "低"
        else:
            level = "极低"
        
        return {
            'score': security_score,
            'level': level,
            'issues': issues,
            'password_length': len(password),
            'has_custom_salt': bool(salt_hex and salt_hex != 'rwa_hub_salt_2025'.encode().hex())
        }

# 全局实例
improved_crypto_manager = None

def get_improved_crypto_manager() -> ImprovedCryptoManager:
    """获取改进的加密管理器实例"""
    global improved_crypto_manager
    if improved_crypto_manager is None:
        improved_crypto_manager = ImprovedCryptoManager()
    return improved_crypto_manager

def generate_secure_config():
    """生成安全的加密配置"""
    password = secrets.token_urlsafe(48)  # 64字符强密码
    salt = secrets.token_bytes(32)  # 32字节随机盐值
    
    return {
        'password': password,
        'salt_hex': salt.hex(),
        'salt_bytes': salt
    }