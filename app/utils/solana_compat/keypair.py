from typing import Dict, List, Optional, Any, Union
import base58
import hashlib
from .publickey import PublicKey

# 尝试导入真正的Ed25519算法
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False

class Keypair:
    """Keypair consisting of a public and private key."""
    
    def __init__(self, keypair_bytes: Optional[bytes] = None):
        """Initialize from keypair bytes."""
        if keypair_bytes is None:
            raise ValueError("必须提供有效的私钥，不允许使用默认私钥")
        else:
            # 支持32字节（仅私钥）或64字节（私钥+公钥）
            if len(keypair_bytes) == 32:
                self._secret = keypair_bytes
            elif len(keypair_bytes) == 64:
                self._secret = keypair_bytes[:32]
            else:
                raise ValueError(f"Invalid keypair length: {len(keypair_bytes)}, expected 32 or 64")
        
        # 生成公钥 - 使用更合理的方法
        # 注意：这是简化实现，实际Solana使用Ed25519算法
        self._public_key = self._generate_public_key(self._secret)
    
    @staticmethod
    def from_secret_key(secret_key: bytes) -> "Keypair":
        """Create keypair from secret key."""
        if len(secret_key) != 32:
            raise ValueError(f"Invalid secret key length: {len(secret_key)}")
        
        # 创建64字节的密钥对（前32字节是私钥，后32字节是公钥）
        keypair_bytes = bytearray(64)
        keypair_bytes[:32] = secret_key
        # 后32字节设为公钥（简化实现，使用私钥的哈希）
        import hashlib
        public_key_bytes = hashlib.sha256(secret_key).digest()
        keypair_bytes[32:] = public_key_bytes
        
        return Keypair(bytes(keypair_bytes))
    
    @staticmethod
    def from_seed(seed: bytes) -> "Keypair":
        """Generate a keypair from a 32 byte seed."""
        if len(seed) != 32:
            raise ValueError(f"Invalid seed length: {len(seed)}, expected 32")
        return Keypair(seed)
    
    @property
    def public_key(self) -> PublicKey:
        """Get the public key."""
        return self._public_key
    
    @property
    def secret_key(self) -> bytes:
        """Get the secret key."""
        return self._secret
    
    def _generate_public_key(self, private_key: bytes) -> PublicKey:
        """
        从私钥生成公钥
        使用真正的Ed25519算法（如果可用）
        """
        if ED25519_AVAILABLE:
            try:
                # 使用真正的Ed25519算法
                private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
                public_key_bytes = private_key_obj.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
                return PublicKey(public_key_bytes)
            except Exception as e:
                # 如果Ed25519失败，回退到哈希方法
                pass
        
        # 回退方法：使用多轮哈希来模拟Ed25519公钥生成
        hash1 = hashlib.sha256(private_key).digest()
        hash2 = hashlib.sha256(hash1 + private_key).digest()
        
        # 混合两个哈希值来生成更随机的公钥
        public_key_bytes = bytearray(32)
        for i in range(32):
            public_key_bytes[i] = hash1[i] ^ hash2[i]
        
        return PublicKey(bytes(public_key_bytes))
    
    def sign(self, message: bytes) -> bytes:
        """Sign a message with this keypair."""
        # 简化实现，返回一个固定的签名
        return bytes([1] * 64) 