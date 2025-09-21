"""
Keypair类的简化实现
兼容solana-py库的Keypair功能
"""

import hashlib
from typing import Optional
from .publickey import PublicKey


class Keypair:
    """Solana密钥对类 - 兼容solana-py"""

    def __init__(self, secret_key: Optional[bytes] = None):
        """初始化密钥对"""
        if secret_key is None:
            # 生成随机私钥
            import secrets
            self._secret_key = secrets.token_bytes(32)
        else:
            if len(secret_key) not in [32, 64]:  # 支持32字节私钥或64字节完整密钥对
                raise ValueError(f"Invalid secret key length: {len(secret_key)}")
            # 只取前32字节作为私钥
            self._secret_key = secret_key[:32]

        # 从私钥生成公钥
        self._public_key = self._generate_public_key()

    @classmethod
    def from_secret_key(cls, secret_key: bytes) -> 'Keypair':
        """从私钥创建密钥对"""
        return cls(secret_key)

    @classmethod
    def from_seed(cls, seed: bytes) -> 'Keypair':
        """从种子创建密钥对"""
        if len(seed) != 32:
            raise ValueError("Seed must be 32 bytes")
        return cls(seed)

    @property
    def public_key(self) -> PublicKey:
        """获取公钥"""
        return self._public_key

    @property
    def secret_key(self) -> bytes:
        """获取私钥"""
        return self._secret_key

    def _generate_public_key(self) -> PublicKey:
        """从私钥生成公钥（简化实现）"""
        # 这是一个简化的实现，实际应使用Ed25519算法
        # 这里使用哈希来模拟公钥生成
        hash_result = hashlib.sha256(self._secret_key + b"public_key").digest()
        return PublicKey(hash_result)

    def sign(self, message: bytes) -> bytes:
        """签名消息（简化实现）"""
        # 这是一个简化的签名实现，实际应使用Ed25519签名
        signature_hash = hashlib.sha256(self._secret_key + message).digest()
        # Solana签名是64字节，这里重复哈希来达到64字节
        return signature_hash + hashlib.sha256(signature_hash).digest() 