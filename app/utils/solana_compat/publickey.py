"""
PublicKey类的完整实现
兼容solana-py库的PublicKey功能
"""

import base58
from typing import Union


class PublicKey:
    """Solana公钥类 - 兼容solana-py"""

    LENGTH = 32  # Solana公钥长度

    def __init__(self, value: Union[str, bytes, 'PublicKey']):
        """初始化PublicKey对象"""
        if isinstance(value, str):
            # Base58编码的字符串
            try:
                self._bytes = base58.b58decode(value)
                if len(self._bytes) != self.LENGTH:
                    raise ValueError(f"Invalid public key length: {len(self._bytes)}")
            except Exception as e:
                raise ValueError(f"Invalid base58 string: {value}") from e
        elif isinstance(value, bytes):
            # 字节数组
            if len(value) != self.LENGTH:
                raise ValueError(f"Public key must be {self.LENGTH} bytes")
            self._bytes = value
        elif isinstance(value, PublicKey):
            # 另一个PublicKey实例
            self._bytes = value._bytes
        else:
            raise ValueError(f"Invalid PublicKey type: {type(value)}")

    def __str__(self) -> str:
        """返回Base58编码的字符串"""
        return base58.b58encode(self._bytes).decode('utf-8')

    def __repr__(self) -> str:
        return f"PublicKey('{str(self)}')"

    def __eq__(self, other) -> bool:
        """比较两个公钥是否相等"""
        if isinstance(other, PublicKey):
            return self._bytes == other._bytes
        elif isinstance(other, str):
            try:
                return self._bytes == base58.b58decode(other)
            except Exception:
                return False
        return False

    def __hash__(self) -> int:
        """返回公钥的哈希值"""
        return hash(self._bytes)

    @property
    def bytes(self) -> bytes:
        """返回32字节的公钥数据"""
        return self._bytes

    def to_base58(self) -> str:
        """返回Base58编码的字符串"""
        return str(self)

    def to_bytes(self) -> bytes:
        """返回字节数组"""
        return self._bytes

    @classmethod
    def from_string(cls, value: str) -> 'PublicKey':
        """从Base58字符串创建PublicKey"""
        return cls(value)

    @classmethod
    def from_bytes(cls, value: bytes) -> 'PublicKey':
        """从字节数组创建PublicKey"""
        return cls(value) 