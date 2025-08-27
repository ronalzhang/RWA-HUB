"""
Solana区块链核心服务
- 提供一个到Solana节点的、标准化的客户端连接。
- 使用官方 `solana-py` 和 `solders` 库。
- 移除了所有旧的、非标准的兼容层代码。
"""

import logging
from functools import lru_cache
from flask import current_app

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.hash import Hash
from solana.exceptions import SolanaRpcException
import base58

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_solana_client() -> Client:
    """
    获取一个共享的Solana RPC客户端实例。
    使用lru_cache确保在单个应用上下文中只创建一个客户端。
    """
    rpc_url = current_app.config.get('SOLANA_RPC_URL')
    if not rpc_url:
        logger.error("SOLANA_RPC_URL 未在配置中设置!")
        raise ValueError("SOLANA_RPC_URL is not configured.")
    
    logger.info(f"创建 Solana 客户端，连接到: {rpc_url}")
    return Client(rpc_url)

def validate_solana_address(address: str) -> bool:
    """
    验证Solana地址格式是否有效。
    """
    if not isinstance(address, str):
        return False
    try:
        # 一个有效的Solana地址是32字节的base58编码字符串
        decoded = base58.b58decode(address)
        return len(decoded) == 32
    except (ValueError, Exception):
        return False

def get_latest_blockhash() -> str:
    """
    获取最新的区块哈希，用于交易。
    返回字符串格式，由调用方转换为Hash类型。
    """
    try:
        client = get_solana_client()
        resp = client.get_latest_blockhash()
        if resp.value and resp.value.blockhash:
            blockhash_str = str(resp.value.blockhash)
            logger.debug(f"获取到最新区块哈希: {blockhash_str[:8]}...")
            return blockhash_str
        else:
            raise SolanaRpcException(f"未能从节点获取有效的区块哈希: {resp}")
    except Exception as e:
        logger.error(f"获取最新区块哈希失败: {e}", exc_info=True)
        raise

def get_latest_blockhash_with_cache(cache_duration: int = 30) -> str:
    """
    获取最新的区块哈希，带缓存功能以减少RPC调用。
    
    Args:
        cache_duration: 缓存持续时间（秒），默认30秒
    
    Returns:
        str: 区块哈希字符串
    """
    import time
    
    # 简单的内存缓存实现
    if not hasattr(get_latest_blockhash_with_cache, '_cache'):
        get_latest_blockhash_with_cache._cache = {}
    
    cache = get_latest_blockhash_with_cache._cache
    current_time = time.time()
    
    # 检查缓存是否有效
    if 'blockhash' in cache and 'timestamp' in cache:
        if current_time - cache['timestamp'] < cache_duration:
            logger.debug(f"使用缓存的区块哈希: {cache['blockhash'][:8]}...")
            return cache['blockhash']
    
    # 获取新的区块哈希
    try:
        blockhash = get_latest_blockhash()
        cache['blockhash'] = blockhash
        cache['timestamp'] = current_time
        logger.debug(f"缓存新的区块哈希: {blockhash[:8]}...")
        return blockhash
    except Exception as e:
        # 如果获取失败且有缓存，使用过期的缓存作为回退
        if 'blockhash' in cache:
            logger.warning(f"获取区块哈希失败，使用过期缓存: {e}")
            return cache['blockhash']
        raise