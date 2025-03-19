"""
助记词和钱包辅助工具模块
"""
import os
import logging
import base58
from mnemonic import Mnemonic
from bip32utils import BIP32Key

logger = logging.getLogger(__name__)

def validate_mnemonic(mnemonic_phrase):
    """
    验证助记词是否有效
    
    Args:
        mnemonic_phrase: 12或24个单词的助记词，用空格分隔
        
    Returns:
        bool: 是否有效
    """
    try:
        if not mnemonic_phrase or not isinstance(mnemonic_phrase, str):
            logger.error("助记词不是有效字符串")
            return False
            
        # 清理和规范化
        cleaned_phrase = ' '.join(mnemonic_phrase.strip().split())
        
        # 验证助记词单词数量
        words = cleaned_phrase.split()
        if len(words) not in (12, 24):
            logger.error(f"助记词单词数量错误: {len(words)}, 应该是12或24")
            return False
            
        # 使用BIP39标准验证
        mnemo = Mnemonic("english")
        is_valid = mnemo.check(cleaned_phrase)
        
        if not is_valid:
            logger.error("助记词未通过BIP39验证")
        
        return is_valid
    except Exception as e:
        logger.exception(f"验证助记词时发生错误: {str(e)}")
        return False

def load_wallet_from_env():
    """
    从环境变量加载钱包凭证
    
    返回优先顺序:
    1. SOLANA_SERVICE_WALLET_MNEMONIC (作为助记词)
    2. SOLANA_SERVICE_WALLET_PRIVATE_KEY (作为私钥)
    
    Returns:
        dict: 包含类型和值的字典，如果未找到则返回None
    """
    # 检查助记词
    if 'SOLANA_SERVICE_WALLET_MNEMONIC' in os.environ:
        mnemonic = os.environ.get('SOLANA_SERVICE_WALLET_MNEMONIC')
        if validate_mnemonic(mnemonic):
            return {
                'type': 'mnemonic',
                'value': mnemonic
            }
        else:
            logger.error("环境变量中的助记词无效")
            
    # 检查私钥
    if 'SOLANA_SERVICE_WALLET_PRIVATE_KEY' in os.environ:
        private_key = os.environ.get('SOLANA_SERVICE_WALLET_PRIVATE_KEY')
        try:
            # 简单验证base58格式
            decoded = base58.b58decode(private_key)
            if len(decoded) == 64:  # Solana私钥长度
                return {
                    'type': 'private_key',
                    'value': private_key
                }
            else:
                logger.error(f"私钥长度不正确: {len(decoded)}字节，应为64字节")
        except Exception as e:
            logger.error(f"环境变量中的私钥格式无效: {str(e)}")
    
    # 未找到有效凭证
    logger.warning("环境变量中未找到有效的钱包凭证")
    
    # 查找相关环境变量以便调试
    env_vars = {k: v[:3] + '...' if k.endswith('KEY') or k.endswith('MNEMONIC') else v 
                for k, v in os.environ.items() if k.startswith('SOLANA_')}
    
    if env_vars:
        logger.info(f"找到SOLANA相关环境变量: {list(env_vars.keys())}")
    else:
        logger.warning("未找到任何SOLANA_开头的环境变量")
        
    return None 