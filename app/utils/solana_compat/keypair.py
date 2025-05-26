from typing import Dict, List, Optional, Any, Union
import base58
from .publickey import PublicKey

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
        
        # 生成公钥
        self._public_key = PublicKey(self._secret)
    
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
    
    def sign(self, message: bytes) -> bytes:
        """Sign a message with this keypair."""
        # 简化实现，返回一个固定的签名
        return bytes([1] * 64) 