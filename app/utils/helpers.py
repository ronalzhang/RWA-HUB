import logging
import os
import base64
import base58
from typing import Optional, Union, Dict, Any

# 使用兼容层而不是直接导入solana库
from app.utils.solana_compat.keypair import Keypair

# 添加加密管理器导入
try:
    from .crypto_manager import get_decrypted_private_key, get_crypto_manager
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("加密管理器不可用，将使用明文私钥")

logger = logging.getLogger(__name__)

def check_response(response, label="API"):
    """
    检查API响应是否有效，记录错误并返回结果
    
    Args:
        response: API响应对象
        label: 用于日志的API标识
        
    Returns:
        bool: 响应是否成功
    """
    if response and "result" in response:
        return True
    
    error_msg = f"{label}请求失败"
    if response and "error" in response:
        error_msg += f": {response['error']['message']}"
    else:
        error_msg += ": 未知错误"
    
    logger.error(error_msg)
    return False


def get_solana_keypair_from_env(var_name: str = "SOLANA_PRIVATE_KEY") -> Optional[dict]:
    """
    从环境变量获取Solana密钥对，支持加密和明文私钥
    
    优先级：
    1. 加密私钥 (SOLANA_PRIVATE_KEY_ENCRYPTED)
    2. 明文私钥 (SOLANA_PRIVATE_KEY)
    
    Args:
        var_name: 环境变量名称
        
    Returns:
        包含private_key和public_key的字典，如果失败返回None
    """
    logger = logging.getLogger(__name__)
    
    # 首先尝试获取加密的私钥
    if CRYPTO_AVAILABLE:
        try:
            private_key_str = get_decrypted_private_key('SOLANA_PRIVATE_KEY_ENCRYPTED')
            logger.info("成功从加密存储获取私钥")
        except Exception as e:
            logger.info(f"无法从加密存储获取私钥: {e}")
            private_key_str = None
    else:
        private_key_str = None
    
    # 如果加密私钥不可用，尝试明文私钥（向后兼容）
    if not private_key_str:
        private_key_str = os.environ.get(var_name)
        if private_key_str:
            logger.warning("使用明文私钥（不安全），建议迁移到加密存储")
    
    if not private_key_str:
        logger.error("未找到Solana私钥")
        return None
    
    try:
        # 检测私钥格式并转换
        if len(private_key_str) == 128:  # 十六进制格式
            private_key_bytes = bytes.fromhex(private_key_str)
        elif len(private_key_str) == 88:  # Base64格式
            private_key_bytes = base64.b64decode(private_key_str)
        else:  # Base58格式
            private_key_bytes = base58.b58decode(private_key_str)
        
        # 如果是64字节，取前32字节作为seed
        if len(private_key_bytes) == 64:
            seed = private_key_bytes[:32]
        elif len(private_key_bytes) == 32:
            seed = private_key_bytes
        else:
            raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}")
        
        # 创建密钥对
        keypair = Keypair.from_seed(seed)
        
        return {
            'private_key': base58.b58encode(seed).decode(),
            'public_key': str(keypair.public_key),
            'keypair': keypair
        }
        
    except Exception as e:
        logger.error(f"解析Solana私钥失败: {e}")
        return None 