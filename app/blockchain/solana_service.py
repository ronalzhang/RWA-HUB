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
    """
    try:
        client = get_solana_client()
        resp = client.get_latest_blockhash()
        if resp.value and resp.value.blockhash:
            return str(resp.value.blockhash)
        else:
            raise SolanaRpcException(f"未能从节点获取有效的区块哈希: {resp}")
    except Exception as e:
        logger.error(f"获取最新区块哈希失败: {e}", exc_info=True)
        raise