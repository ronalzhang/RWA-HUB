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


def get_solana_keypair_from_env(var_name: str = "SOLANA_PRIVATE_KEY") -> Optional[dict]:
    """
    从环境变量获取Solana私钥
    
    Args:
        var_name: 环境变量名称
        
    Returns:
        dict: 包含私钥信息的字典，格式为 {'value': private_key_string, 'type': 'base58|base64|hex'}
              如果找不到则返回None
    """
    private_key = os.environ.get(var_name)
    if not private_key:
        logger.error(f"环境变量 {var_name} 未设置")
        return None
    
    # 检测私钥格式并返回原始字符串
    private_key = private_key.strip()
    
    # 检测是否为Base58格式（Solana标准格式，通常88个字符）
    if len(private_key) == 88:
        try:
            # 验证Base58解码是否成功且长度正确
            decoded = base58.b58decode(private_key)
            if len(decoded) == 64:  # Solana私钥应该是64字节（包含公钥部分）
                logger.info(f"检测到Base58格式的Solana私钥")
                return {'value': private_key, 'type': 'base58'}
        except Exception as e:
            logger.warning(f"Base58格式验证失败: {str(e)}")
    
    # 检测是否为十六进制格式（128个字符）
    elif len(private_key) == 128:
        try:
            # 验证十六进制解码
            decoded = bytes.fromhex(private_key)
            if len(decoded) == 64:
                logger.info(f"检测到十六进制格式的Solana私钥")
                return {'value': private_key, 'type': 'hex'}
        except Exception as e:
            logger.warning(f"十六进制格式验证失败: {str(e)}")
    
    # 检测是否为Base64格式
    elif len(private_key) in [86, 87, 88]:  # Base64编码的64字节数据
        try:
            decoded = base64.b64decode(private_key)
            if len(decoded) == 64:
                logger.info(f"检测到Base64格式的Solana私钥")
                return {'value': private_key, 'type': 'base64'}
        except Exception as e:
            logger.warning(f"Base64格式验证失败: {str(e)}")
    
    # 如果都不匹配，尝试作为Base58处理（最常见的格式）
    try:
        decoded = base58.b58decode(private_key)
        if len(decoded) == 64:
            logger.info(f"使用Base58成功解码私钥（长度: {len(private_key)}）")
            return {'value': private_key, 'type': 'base58'}
    except Exception as e:
        logger.warning(f"Base58解码失败: {str(e)}")
    
    logger.error(f"无法识别私钥格式，长度: {len(private_key)}，支持的格式：base58(88字符), hex(128字符), base64(86-88字符)")
    return None 