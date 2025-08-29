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

def get_latest_blockhash() -> Hash:
    """
    获取最新的区块哈希，用于交易。
    返回Hash类型，包含详细的错误处理和重试逻辑。
    """
    max_retries = 3
    retry_delay = 1.0
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"区块哈希检索重试 {attempt}/{max_retries}")
                import time
                time.sleep(retry_delay * attempt)  # 指数退避
            
            logger.debug("开始获取最新区块哈希")
            client = get_solana_client()
            
            # 添加超时处理
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10.0)  # 10秒超时
            
            try:
                resp = client.get_latest_blockhash()
                
                if not resp:
                    raise SolanaRpcException("RPC响应为空")
                    
                if not resp.value:
                    raise SolanaRpcException(f"RPC响应值为空: {resp}")
                    
                if not resp.value.blockhash:
                    raise SolanaRpcException(f"区块哈希为空: {resp.value}")
                
                # 直接返回Hash对象，不需要字符串转换
                blockhash = resp.value.blockhash
                
                # 验证区块哈希是否有效
                if not _validate_blockhash(blockhash):
                    raise SolanaRpcException(f"区块哈希验证失败: {blockhash}")
                
                logger.debug(f"成功获取最新区块哈希: {str(blockhash)[:8]}...")
                return blockhash
                
            finally:
                socket.setdefaulttimeout(original_timeout)
                
        except SolanaRpcException as e:
            last_exception = e
            logger.warning(f"Solana RPC获取区块哈希失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt == max_retries:
                break
        except socket.timeout as e:
            last_exception = e
            logger.warning(f"获取区块哈希超时 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt == max_retries:
                break
        except ConnectionError as e:
            last_exception = e
            logger.warning(f"获取区块哈希连接错误 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt == max_retries:
                break
        except Exception as e:
            last_exception = e
            logger.warning(f"获取最新区块哈希未知错误 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt == max_retries:
                break
    
    # 所有重试都失败了
    logger.error(f"区块哈希检索最终失败，已重试 {max_retries} 次")
    if isinstance(last_exception, SolanaRpcException):
        raise Exception(f"RPC错误: {str(last_exception)}")
    elif isinstance(last_exception, socket.timeout):
        raise Exception("网络超时，请稍后重试")
    elif isinstance(last_exception, ConnectionError):
        raise Exception("网络连接失败，请检查网络设置")
    else:
        raise Exception(f"获取区块哈希失败: {str(last_exception)}")

def _validate_blockhash(blockhash: Hash) -> bool:
    """
    验证检索到的区块哈希是否有效
    
    Args:
        blockhash: 要验证的区块哈希
        
    Returns:
        bool: 区块哈希是否有效
    """
    try:
        if not blockhash:
            logger.error("区块哈希为空")
            return False
        
        # 转换为字符串进行长度验证
        blockhash_str = str(blockhash)
        
        # 验证区块哈希格式 - Solana区块哈希应该是32字节的base58编码
        if len(blockhash_str) < 32:
            logger.error(f"区块哈希格式无效，长度过短: {len(blockhash_str)}")
            return False
        
        # 验证是否为有效的base58编码
        try:
            import base58
            decoded = base58.b58decode(blockhash_str)
            if len(decoded) != 32:
                logger.error(f"区块哈希解码后长度无效: {len(decoded)} != 32")
                return False
        except Exception as e:
            logger.error(f"区块哈希base58解码失败: {e}")
            return False
        
        logger.debug(f"区块哈希验证通过: {blockhash_str[:8]}...")
        return True
        
    except Exception as e:
        logger.error(f"区块哈希验证过程中发生错误: {e}")
        return False

def get_latest_blockhash_with_cache(cache_duration: int = 30) -> Hash:
    """
    获取最新的区块哈希，带缓存功能以减少RPC调用。
    包含优雅的回退机制处理瞬态连接问题。
    
    Args:
        cache_duration: 缓存持续时间（秒），默认30秒
    
    Returns:
        Hash: 区块哈希对象
        
    Raises:
        Exception: 无法获取区块哈希且无可用缓存时抛出异常
    """
    import time
    
    # 简单的内存缓存实现
    if not hasattr(get_latest_blockhash_with_cache, '_cache'):
        get_latest_blockhash_with_cache._cache = {}
    
    cache = get_latest_blockhash_with_cache._cache
    current_time = time.time()
    
    # 检查缓存是否有效
    if 'blockhash' in cache and 'timestamp' in cache:
        cache_age = current_time - cache['timestamp']
        if cache_age < cache_duration:
            cached_hash = cache['blockhash']
            logger.debug(f"使用缓存的区块哈希: {str(cached_hash)[:8]}... (缓存年龄: {cache_age:.1f}秒)")
            return cached_hash
        else:
            logger.debug(f"缓存已过期: {cache_age:.1f}秒 > {cache_duration}秒，尝试获取新的区块哈希")
    
    # 获取新的区块哈希
    try:
        logger.debug("尝试获取新的区块哈希")
        blockhash = get_latest_blockhash()
        
        # 在缓存前再次验证区块哈希
        if not _validate_blockhash(blockhash):
            raise Exception("获取的区块哈希验证失败")
        
        cache['blockhash'] = blockhash
        cache['timestamp'] = current_time
        logger.debug(f"成功缓存新的区块哈希: {str(blockhash)[:8]}...")
        return blockhash
        
    except Exception as e:
        logger.warning(f"获取新区块哈希失败: {e}")
        
        # 如果获取失败且有缓存，使用过期的缓存作为回退
        if 'blockhash' in cache:
            cache_age = current_time - cache['timestamp']
            max_stale_age = cache_duration * 3  # 允许使用3倍缓存时间的过期缓存
            
            if cache_age < max_stale_age:
                cached_hash = cache['blockhash']
                # 验证过期缓存是否仍然有效
                if _validate_blockhash(cached_hash):
                    logger.warning(f"使用过期缓存作为回退: {str(cached_hash)[:8]}... (过期 {cache_age:.1f}秒)")
                    return cached_hash
                else:
                    logger.error("过期缓存验证失败，无法使用")
            else:
                logger.error(f"缓存过于陈旧 ({cache_age:.1f}秒 > {max_stale_age}秒)，无法使用")
        else:
            logger.error("无可用缓存")
        
        # 重新抛出原始异常
        raise Exception(f"无法获取区块哈希且无可用缓存: {str(e)}")

def clear_blockhash_cache():
    """
    清除区块哈希缓存，用于测试或强制刷新
    """
    if hasattr(get_latest_blockhash_with_cache, '_cache'):
        get_latest_blockhash_with_cache._cache.clear()
        logger.info("区块哈希缓存已清除")

def get_blockhash_cache_status() -> dict:
    """
    获取区块哈希缓存状态，用于监控和调试
    
    Returns:
        dict: 包含缓存状态信息的字典
    """
    import time
    
    if not hasattr(get_latest_blockhash_with_cache, '_cache'):
        return {'cached': False, 'message': '无缓存'}
    
    cache = get_latest_blockhash_with_cache._cache
    
    if 'blockhash' not in cache or 'timestamp' not in cache:
        return {'cached': False, 'message': '缓存为空'}
    
    current_time = time.time()
    cache_age = current_time - cache['timestamp']
    cached_hash = cache['blockhash']
    
    return {
        'cached': True,
        'blockhash': str(cached_hash)[:8] + '...',
        'age_seconds': cache_age,
        'timestamp': cache['timestamp'],
        'is_fresh': cache_age < 30,  # 默认缓存时间
        'is_valid': _validate_blockhash(cached_hash)
    }

def check_transaction(signature: str) -> dict:
    """
    检查Solana交易状态
    
    Args:
        signature: 交易签名
        
    Returns:
        dict: 包含交易状态信息的字典
    """
    try:
        from solana.rpc.api import Client
        
        client = get_solana_client()
        
        # 获取交易状态
        response = client.get_signature_statuses([signature], search_transaction_history=True)
        
        if response.value and len(response.value) > 0:
            status_info = response.value[0]
            
            if status_info is None:
                return {
                    "success": True, 
                    "confirmed": False,
                    "status": "not_found",
                    "message": "交易未找到或尚未处理"
                }
            
            confirmed = status_info.confirmation_status in ["confirmed", "finalized"]
            
            return {
                "success": True,
                "confirmed": confirmed,
                "status": status_info.confirmation_status,
                "slot": status_info.slot,
                "err": status_info.err,
                "message": "交易已确认" if confirmed else "交易待确认"
            }
        else:
            return {
                "success": False,
                "error": "无法获取交易状态"
            }
            
    except Exception as e:
        logger.error(f"检查交易状态失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def get_usdc_balance(wallet_address: str) -> float:
    """
    获取钱包的USDC代币余额
    
    Args:
        wallet_address: 钱包地址
        
    Returns:
        float: USDC余额（以美元为单位）
        
    Raises:
        Exception: 获取余额失败时抛出异常
    """
    try:
        from solders.pubkey import Pubkey
        from spl.token.instructions import get_associated_token_address
        
        logger.debug(f"开始获取钱包 {wallet_address} 的USDC余额")
        
        # 验证钱包地址格式
        if not validate_solana_address(wallet_address):
            raise ValueError(f"无效的钱包地址格式: {wallet_address}")
        
        # USDC代币铸造地址（Mainnet生产环境）
        # Mainnet USDC: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
        # Devnet USDC: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
        usdc_mint_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        # 转换地址为PublicKey
        wallet_pubkey = Pubkey.from_string(wallet_address)
        usdc_mint_pubkey = Pubkey.from_string(usdc_mint_address)
        
        # 计算关联代币账户地址
        associated_token_address = get_associated_token_address(wallet_pubkey, usdc_mint_pubkey)
        
        logger.debug(f"计算的关联代币账户地址: {associated_token_address}")
        
        # 获取Solana客户端
        client = get_solana_client()
        
        # 获取代币账户信息
        account_info = client.get_account_info(associated_token_address)
        
        if not account_info.value:
            logger.warning(f"钱包 {wallet_address} 没有USDC代币账户")
            return 0.0
        
        # 获取代币账户余额
        balance_response = client.get_token_account_balance(associated_token_address)
        
        if not balance_response.value:
            logger.warning(f"无法获取钱包 {wallet_address} 的USDC余额")
            return 0.0
        
        # 解析余额（USDC有6位小数）
        balance_info = balance_response.value
        balance = float(balance_info.ui_amount or 0)
        
        logger.info(f"钱包 {wallet_address} 的USDC余额: {balance}")
        
        return balance
        
    except Exception as e:
        logger.error(f"获取USDC余额失败 - 钱包: {wallet_address}, 错误: {str(e)}")
        raise Exception(f"获取USDC余额失败: {str(e)}")