import logging
import os
import base64
import base58
from typing import Optional

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


def get_solana_keypair_from_env(var_name: str = "SOLANA_PRIVATE_KEY") -> Optional[bytes]:
    """
    从环境变量获取Solana私钥
    
    Args:
        var_name: 环境变量名称
        
    Returns:
        bytes: 解码后的私钥字节数据，如果找不到则返回None
    """
    private_key = os.environ.get(var_name)
    if not private_key:
        logger.error(f"环境变量 {var_name} 未设置")
        return None
    
    # 尝试base58解码
    try:
        decoded = base58.b58decode(private_key)
        logger.info(f"使用base58成功解码私钥")
        return decoded
    except Exception as e:
        logger.warning(f"base58解码失败: {str(e)}")
    
    # 尝试base64解码
    try:
        decoded = base64.b64decode(private_key)
        logger.info(f"使用base64成功解码私钥")
        return decoded
    except Exception as e:
        logger.warning(f"base64解码失败: {str(e)}")
    
    logger.error(f"无法解码私钥，支持的格式：base58, base64")
    return None 