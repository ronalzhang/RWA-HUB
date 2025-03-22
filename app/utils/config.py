"""
配置管理工具
用于从环境变量或配置文件加载应用配置
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    # 区块链配置
    "SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com",
    "SOLANA_WALLET_PRIVATE_KEY": "",
    "ETH_RPC_URL": "https://mainnet.infura.io/v3/your-infura-key",
    "ETH_WALLET_PRIVATE_KEY": "",
    
    # 应用配置
    "APP_NAME": "RWA-HUB",
    "DEBUG": False,
    
    # 数据库配置在环境变量中设置，这里不提供默认值
    
    # 网络配置
    "API_TIMEOUT": 30,
    "MAX_RETRIES": 3,
    
    # 文件存储配置
    "UPLOAD_FOLDER": "uploads",
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB
    
    # 缓存配置
    "CACHE_TYPE": "simple",
    "CACHE_DEFAULT_TIMEOUT": 300
}

_config_cache = None

def load_config() -> Dict[str, Any]:
    """
    加载配置，优先从环境变量加载，然后是配置文件
    
    Returns:
        Dict[str, Any]: 配置字典
    """
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    config = DEFAULT_CONFIG.copy()
    
    # 从环境变量加载配置
    for key in config.keys():
        env_value = os.getenv(key)
        if env_value:
            # 尝试将值转换为合适的类型
            if env_value.lower() in ('true', 'yes', '1'):
                config[key] = True
            elif env_value.lower() in ('false', 'no', '0'):
                config[key] = False
            elif env_value.isdigit():
                config[key] = int(env_value)
            elif env_value.replace('.', '', 1).isdigit() and env_value.count('.') <= 1:
                config[key] = float(env_value)
            else:
                config[key] = env_value
    
    # 尝试从配置文件加载
    config_path = os.getenv('CONFIG_FILE', 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
            logger.info(f"已从文件加载配置: {config_path}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
    
    _config_cache = config
    return config

def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值
    
    Args:
        key: 配置键名
        default: 默认值，如果配置不存在则返回该值
        
    Returns:
        Any: 配置值
    """
    config = load_config()
    return config.get(key, default)

def set_config(key: str, value: Any) -> None:
    """
    设置配置值（仅在内存中，不会保存到文件）
    
    Args:
        key: 配置键名
        value: 配置值
    """
    config = load_config()
    config[key] = value
    
def save_config(config_path: Optional[str] = None) -> bool:
    """
    保存配置到文件
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认路径
        
    Returns:
        bool: 是否成功
    """
    config = load_config()
    if config_path is None:
        config_path = os.getenv('CONFIG_FILE', 'config.json')
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"配置已保存到文件: {config_path}")
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return False 