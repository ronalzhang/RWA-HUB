import base58
import base64
import binascii
import hashlib
import re
from typing import List, Optional, Union, Any, Dict, Tuple

class PublicKey:
    """
    Solana公钥兼容层实现
    兼容solana-py库的PublicKey类
    """
    
    LENGTH = 32  # 公钥标准长度
    
    def __init__(self, value: Union[str, bytes, List[int], int, 'PublicKey']) -> None:
        """
        初始化PublicKey对象
        支持多种格式的输入，包括字符串、字节数组、整数列表、整数以及PublicKey对象
        """
        if isinstance(value, str):
            # 如果是字符串，直接解码
            try:
                # 可能是base58编码的字符串
                bytes_array = base58.b58decode(value)
                if len(bytes_array) != self.LENGTH:
                    # 如果长度不对，尝试填充或截断
                    if len(bytes_array) < self.LENGTH:
                        # 填充到32字节
                        bytes_array = bytes_array + b'\x00' * (self.LENGTH - len(bytes_array))
                    else:
                        # 截断到32字节
                        bytes_array = bytes_array[:self.LENGTH]
                self._key = bytes(bytes_array)
            except Exception as e:
                raise ValueError(f"无效的公钥格式: {str(e)}")
        elif isinstance(value, bytes):
            # 如果是字节数组，直接使用
            if len(value) != self.LENGTH:
                # 如果长度不对，尝试填充或截断
                if len(value) < self.LENGTH:
                    # 填充到32字节
                    value = value + b'\x00' * (self.LENGTH - len(value))
                else:
                    # 截断到32字节
                    value = value[:self.LENGTH]
            self._key = bytes(value)
        elif isinstance(value, list):
            # 如果是整数列表，转换为字节数组
            if len(value) != self.LENGTH:
                raise ValueError(f"无效的公钥长度: {len(value)}")
            self._key = bytes(value)
        elif isinstance(value, int):
            # 如果是整数，转换为字节数组
            buf = [0] * self.LENGTH
            i = self.LENGTH - 1
            while i >= 0:
                buf[i] = value & 0xff
                value >>= 8
                i -= 1
            self._key = bytes(buf)
        elif isinstance(value, PublicKey):
            # 如果是PublicKey对象，复制其内部值
            self._key = bytes(value._key)
        else:
            raise TypeError("不支持的公钥类型")
    
    def __str__(self) -> str:
        """返回公钥的base58编码字符串表示"""
        return base58.b58encode(self._key).decode('ascii')
    
    def __repr__(self) -> str:
        """返回公钥的详细表示"""
        return f"PublicKey({self.__str__()})"
    
    def __eq__(self, other: Any) -> bool:
        """比较两个公钥是否相等"""
        if not isinstance(other, PublicKey):
            return False
        return self._key == other._key
    
    def __hash__(self) -> int:
        """返回公钥的哈希值"""
        return hash(self._key)
    
    def toBase58(self) -> str:
        """返回公钥的base58编码字符串"""
        return base58.b58encode(self._key).decode('ascii')
    
    def toBytes(self) -> bytes:
        """返回公钥的字节数组"""
        return self._key
    
    def toBuffer(self) -> bytes:
        """返回公钥的字节缓冲区（兼容方法）"""
        return self._key
    
    @staticmethod
    def isOnCurve(pubkey: Union[str, bytes, 'PublicKey']) -> bool:
        """
        检查公钥是否在曲线上
        简化实现，始终返回True
        """
        # 在实际应用中应该进行实际的曲线验证
        # 这里简化为假设所有有效格式的公钥都在曲线上
        try:
            if isinstance(pubkey, (str, bytes)):
                PublicKey(pubkey)
            return True
        except:
            return False
    
    @staticmethod
    def create_with_seed(
        from_public_key: 'PublicKey', 
        seed: str, 
        program_id: 'PublicKey'
    ) -> 'PublicKey':
        """
        使用种子创建派生公钥
        简化实现，使用哈希函数模拟
        """
        bytes1 = from_public_key.toBytes()
        bytes2 = seed.encode()
        bytes3 = program_id.toBytes()
        
        # 计算哈希
        all_bytes = bytes1 + bytes2 + bytes3
        hash_bytes = hashlib.sha256(all_bytes).digest()
        
        # 确保长度为32字节
        if len(hash_bytes) > PublicKey.LENGTH:
            hash_bytes = hash_bytes[:PublicKey.LENGTH]
        
        return PublicKey(hash_bytes)
    
    @staticmethod
    def create_program_address(
        seeds: List[bytes], 
        program_id: 'PublicKey'
    ) -> 'PublicKey':
        """
        创建程序地址
        简化实现，使用哈希函数模拟
        """
        buffer = b""
        for seed in seeds:
            if len(seed) > 32:
                raise ValueError("种子长度不能超过32字节")
            buffer += seed
        
        buffer += program_id.toBytes()
        buffer += b"ProgramDerivedAddress"
        
        hash_bytes = hashlib.sha256(buffer).digest()
        
        # 检查是否在曲线上
        # 实际上应该进行真正的检查，这里简化处理
        if hash_bytes[0] == 0:  # 简化的检查，实际应更复杂
            raise RuntimeError("无效的程序地址")
        
        return PublicKey(hash_bytes)
    
    @staticmethod
    def find_program_address(
        seeds: List[bytes], 
        program_id: 'PublicKey'
    ) -> Tuple['PublicKey', int]:
        """
        查找有效的程序地址和对应的nonce
        简化实现
        """
        nonce = 255
        while nonce > 0:
            try:
                seed_with_nonce = seeds.copy()
                seed_with_nonce.append(bytes([nonce]))
                address = PublicKey.create_program_address(seed_with_nonce, program_id)
                return address, nonce
            except:
                nonce -= 1
                continue
        
        raise RuntimeError("无法找到有效的程序地址") 