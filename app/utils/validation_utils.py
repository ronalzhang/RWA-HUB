"""
统一验证工具类
提供统一的地址验证、数据验证等功能
"""

import re
import base58
from typing import Optional, Union, Any
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


class ValidationUtils:
    """统一验证工具类"""
    
    # 地址格式正则表达式
    ETHEREUM_ADDRESS_PATTERN = r'^0x[a-fA-F0-9]{40}$'
    SOLANA_ADDRESS_PATTERN = r'^[1-9A-HJ-NP-Za-km-z]{32,126}$'
    
    @staticmethod
    def validate_solana_address(address: str) -> bool:
        """
        统一的Solana地址验证
        
        Args:
            address (str): 要验证的Solana地址
            
        Returns:
            bool: 地址是否有效
        """
        if not address or not isinstance(address, str):
            return False
        
        try:
            # 长度检查
            if len(address) < 32 or len(address) > 44:
                return False
            
            # 尝试base58解码
            decoded = base58.b58decode(address)
            return len(decoded) == 32
        except Exception:
            return False
    
    @staticmethod
    def validate_ethereum_address(address: str) -> bool:
        """
        统一的以太坊地址验证
        
        Args:
            address (str): 要验证的以太坊地址
            
        Returns:
            bool: 地址是否有效
        """
        if not address or not isinstance(address, str):
            return False
        
        return re.match(ValidationUtils.ETHEREUM_ADDRESS_PATTERN, address) is not None
    
    @staticmethod
    def validate_wallet_address(address: str) -> bool:
        """
        统一的钱包地址验证（支持以太坊和Solana）
        
        Args:
            address (str): 要验证的钱包地址
            
        Returns:
            bool: 地址是否有效
        """
        if not address or not isinstance(address, str):
            return False
        
        # 先尝试以太坊地址格式
        if ValidationUtils.validate_ethereum_address(address):
            return True
        
        # 再尝试Solana地址格式
        if ValidationUtils.validate_solana_address(address):
            return True
        
        return False
    
    @staticmethod
    def normalize_address(address: str) -> str:
        """
        标准化地址格式
        - 以太坊地址转为小写
        - Solana地址保持原始大小写
        
        Args:
            address (str): 原始地址
            
        Returns:
            str: 标准化后的地址
        """
        if not address:
            return address
        
        # 以太坊地址转小写
        if ValidationUtils.validate_ethereum_address(address):
            return address.lower()
        
        # Solana地址保持原样
        return address
    
    @staticmethod
    def validate_positive_number(value: Union[str, int, float, Decimal], 
                                field_name: str = "值") -> bool:
        """
        验证正数
        
        Args:
            value: 要验证的值
            field_name: 字段名称（用于错误消息）
            
        Returns:
            bool: 是否为有效的正数
        """
        try:
            if isinstance(value, str):
                decimal_value = Decimal(value)
            elif isinstance(value, (int, float)):
                decimal_value = Decimal(str(value))
            elif isinstance(value, Decimal):
                decimal_value = value
            else:
                return False
            
            return decimal_value > 0
        except (InvalidOperation, ValueError):
            return False
    
    @staticmethod
    def validate_non_negative_number(value: Union[str, int, float, Decimal], 
                                   field_name: str = "值") -> bool:
        """
        验证非负数
        
        Args:
            value: 要验证的值
            field_name: 字段名称（用于错误消息）
            
        Returns:
            bool: 是否为有效的非负数
        """
        try:
            if isinstance(value, str):
                decimal_value = Decimal(value)
            elif isinstance(value, (int, float)):
                decimal_value = Decimal(str(value))
            elif isinstance(value, Decimal):
                decimal_value = value
            else:
                return False
            
            return decimal_value >= 0
        except (InvalidOperation, ValueError):
            return False
    
    @staticmethod
    def validate_integer_range(value: Union[str, int], 
                             min_val: Optional[int] = None, 
                             max_val: Optional[int] = None) -> bool:
        """
        验证整数范围
        
        Args:
            value: 要验证的值
            min_val: 最小值（可选）
            max_val: 最大值（可选）
            
        Returns:
            bool: 是否在有效范围内
        """
        try:
            int_value = int(value)
            
            if min_val is not None and int_value < min_val:
                return False
            
            if max_val is not None and int_value > max_val:
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_string_length(value: str, 
                             min_length: Optional[int] = None, 
                             max_length: Optional[int] = None) -> bool:
        """
        验证字符串长度
        
        Args:
            value: 要验证的字符串
            min_length: 最小长度（可选）
            max_length: 最大长度（可选）
            
        Returns:
            bool: 长度是否有效
        """
        if not isinstance(value, str):
            return False
        
        length = len(value)
        
        if min_length is not None and length < min_length:
            return False
        
        if max_length is not None and length > max_length:
            return False
        
        return True
    
    @staticmethod
    def validate_required_fields(data: dict, required_fields: list) -> tuple[bool, list]:
        """
        验证必填字段
        
        Args:
            data: 要验证的数据字典
            required_fields: 必填字段列表
            
        Returns:
            tuple: (是否全部有效, 缺失字段列表)
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """
        清理字符串（去除首尾空格，限制长度）
        
        Args:
            value: 原始字符串
            max_length: 最大长度（可选）
            
        Returns:
            str: 清理后的字符串
        """
        if not isinstance(value, str):
            return str(value) if value is not None else ''
        
        cleaned = value.strip()
        
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        return cleaned
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            bool: 邮箱格式是否有效
        """
        if not email or not isinstance(email, str):
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url: URL地址
            
        Returns:
            bool: URL格式是否有效
        """
        if not url or not isinstance(url, str):
            return False
        
        url_pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        return re.match(url_pattern, url) is not None


class ValidationError(Exception):
    """验证错误异常类"""
    
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'message': self.message,
            'field': self.field,
            'code': self.code
        }