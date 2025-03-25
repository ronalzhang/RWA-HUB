#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Solana区块链服务，提供交易构建和处理功能
"""

import base64
import logging
import time
import json
from typing import Tuple, Dict, Any, Optional

from flask import current_app

# 导入Solana兼容工具
from app.utils.solana_compat.connection import Connection
from app.utils.solana_compat.publickey import PublicKey
from app.utils.solana_compat.transaction import Transaction
from app.utils.solana_compat.tx_opts import TxOpts
from app.config import Config
from app.extensions import db
from app.models import Trade
from datetime import datetime

# 获取日志记录器
logger = logging.getLogger(__name__)

# 通用常量
SOLANA_ENDPOINT = Config.SOLANA_RPC_URL or 'https://api.devnet.solana.com'
PROGRAM_ID = Config.SOLANA_PROGRAM_ID or 'RWAxxx111111111111111111111111111111111111'
USDC_MINT = Config.SOLANA_USDC_MINT or 'USCG9aStBYmRbJdY7cBiiqmyNEGqwT6vAxkxfHECdKN'

# 创建Solana连接
solana_connection = Connection(SOLANA_ENDPOINT)

def prepare_transfer_transaction(
    token_symbol: str,
    from_address: str,
    to_address: str,
    amount: float,
    blockhash: str
) -> Tuple[bytes, bytes]:
    """
    准备转账交易数据和消息
    
    Args:
        token_symbol (str): 代币符号
        from_address (str): 发送方地址
        to_address (str): 接收方地址
        amount (float): 转账金额
        blockhash (str): 最新区块哈希
        
    Returns:
        Tuple[bytes, bytes]: 交易数据和消息数据
    """
    try:
        logger.info(f"准备交易数据 - 代币: {token_symbol}, 发送方: {from_address}, 接收方: {to_address}, 金额: {amount}")
        
        # 创建一个模拟交易，仅用于前端测试
        # 在实际环境中，这里应该使用Solana SDK构建真实交易
        
        # 生成一个随机交易ID
        import random
        import struct
        transaction_id = random.randint(1, 1000000)
        
        # 创建一个简单的交易数据结构
        transaction_data = struct.pack("<IQQQI", 
            transaction_id,                         # 交易ID
            int(time.time()),                       # 时间戳
            int(from_address[:16], 16),             # 发送方地址的一部分（截取16个字符当作数字，这是一个简化操作）
            int(to_address[:16], 16),               # 接收方地址的一部分
            int(amount * 1000000)                   # 金额（转换为整数，乘以10^6表示小数点后6位）
        )
        
        # 创建一个简单的消息数据（在实际环境中，这应该是交易数据的一部分）
        message_data = struct.pack("<IQI",
            transaction_id,                         # 交易ID
            int(time.time()),                       # 时间戳
            int(amount * 1000000)                   # 金额
        )
        
        logger.info(f"已成功生成交易数据 - ID: {transaction_id}")
        
        return transaction_data, message_data
        
    except Exception as e:
        logger.error(f"准备交易数据失败: {str(e)}")
        raise Exception(f"准备交易数据失败: {str(e)}")


def send_transaction_with_signature(
    transaction_data: bytes,
    signature_data: bytes,
    public_key: str
) -> str:
    """
    使用签名数据发送交易
    
    Args:
        transaction_data (bytes): 原始交易数据
        signature_data (bytes): 签名数据
        public_key (str): 公钥
        
    Returns:
        str: 交易签名
    """
    try:
        logger.info(f"发送已签名交易 - 公钥: {public_key}")
        
        # 在实际环境中，这里应该将交易数据和签名组合成一个完整的交易，然后发送到Solana网络
        # 现在我们只是模拟这个过程
        
        # 构建完整的交易对象
        transaction = Transaction.from_bytes(transaction_data)
        
        # 添加签名
        transaction.add_signature(PublicKey(public_key), signature_data)
        
        # 发送交易到Solana网络
        result = solana_connection.send_raw_transaction(transaction.serialize())
        
        # 获取交易签名
        signature = result
        
        logger.info(f"交易发送成功 - 签名: {signature}")
        
        return signature
        
    except Exception as e:
        logger.error(f"发送交易失败: {str(e)}")
        raise Exception(f"发送交易失败: {str(e)}")


def execute_backup_transfer(
    token_symbol: str,
    from_address: str,
    to_address: str,
    amount: float
) -> str:
    """
    执行备用模式的转账交易
    这是一个无需客户端签名的备用方案
    
    Args:
        token_symbol (str): 代币符号
        from_address (str): 发送方地址
        to_address (str): 接收方地址
        amount (float): 转账金额
        
    Returns:
        str: 交易签名
    """
    try:
        logger.info(f"执行备用模式转账 - 代币: {token_symbol}, 发送方: {from_address}, 接收方: {to_address}, 金额: {amount}")
        
        # 在真实环境中，这里应该利用后端私钥签名并执行交易
        # 现在我们模拟这个过程
        
        # 生成一个随机的交易签名
        import random
        import hashlib
        
        # 创建一个唯一的种子
        seed = f"{token_symbol}:{from_address}:{to_address}:{amount}:{int(time.time())}"
        
        # 生成签名
        signature = hashlib.sha256(seed.encode()).hexdigest()
        
        logger.info(f"备用模式转账成功 - 签名: {signature}")
        
        return signature
        
    except Exception as e:
        logger.error(f"备用转账失败: {str(e)}")
        raise Exception(f"备用转账失败: {str(e)}")

def prepare_transaction(user_address, asset_id, token_symbol, amount, price, trade_id):
    """
    准备Solana交易数据
    
    Args:
        user_address: 用户钱包地址
        asset_id: 资产ID
        token_symbol: 代币符号
        amount: 交易数量
        price: 代币价格
        trade_id: 交易记录ID
        
    Returns:
        dict: 交易数据
    """
    try:
        logger.info(f"准备Solana交易: 用户={user_address}, 资产ID={asset_id}, 数量={amount}")
        
        # 创建交易
        transaction = Transaction()
        
        # 将交易ID编码到交易备注中
        transaction.add_memo(f"trade:{trade_id}", PublicKey(user_address))
        
        # 创建资产购买指令
        # 根据具体的Solana合约设计来构建指令
        # 这里是简化的示例，实际应用中需要根据合约ABI来构建
        instruction_data = {
            "method": "buy_asset",
            "params": {
                "asset_id": asset_id,
                "token_symbol": token_symbol,
                "amount": amount,
                "price": price,
                "trade_id": trade_id,
                "buyer": user_address
            }
        }
        
        # 将指令数据序列化
        instruction_bytes = json.dumps(instruction_data).encode('utf-8')
        
        # 设置最近的区块哈希
        transaction.set_recent_blockhash("simulated_blockhash_for_dev")
        
        # 将交易序列化为Base64编码
        serialized_tx = base64.b64encode(transaction.serialize()).decode('utf-8')
        
        # 构建Phantom钱包需要的交易格式
        # Phantom钱包需要一个Message对象和Uint8Array对象
        phantom_transaction = {
            "transaction": {
                "recentBlockhash": "simulated_blockhash_for_dev",
                "feePayer": user_address,
                "instructions": [
                    {
                        "programId": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
                        "keys": [{"pubkey": user_address, "isSigner": True, "isWritable": False}],
                        "data": base64.b64encode(f"trade:{trade_id}".encode('utf-8')).decode('utf-8')
                    }
                ],
                "signers": []
            },
            "signers": [],
            "signerPublicKeys": [user_address]
        }
        
        # 返回交易数据
        return phantom_transaction
        
    except Exception as e:
        logger.error(f"准备Solana交易失败: {str(e)}")
        raise Exception(f"准备交易失败: {str(e)}")

def check_transaction(signature):
    """
    检查Solana交易状态
    
    Args:
        signature: 交易签名
        
    Returns:
        dict: 交易状态
    """
    try:
        logger.info(f"检查Solana交易状态: 签名={signature}")
        
        # 查询交易状态
        try:
            # 尝试获取交易确认状态
            tx_result = solana_connection.confirm_transaction(signature)
            
            if tx_result and 'result' in tx_result:
                confirmed = tx_result['result'].get('value', 0) > 0
                confirmations = tx_result['result'].get('value', 0)
                
                return {
                    "confirmed": confirmed,
                    "confirmations": confirmations
                }
            else:
                # 交易未找到或未确认
                return {
                    "confirmed": False,
                    "confirmations": 0,
                    "error": "交易未确认"
                }
                
        except Exception as e:
            logger.error(f"获取交易确认状态失败: {str(e)}")
            return {
                "confirmed": False,
                "confirmations": 0,
                "error": f"获取确认状态失败: {str(e)}"
            }
        
    except Exception as e:
        logger.error(f"检查Solana交易状态失败: {str(e)}")
        return {
            "confirmed": False,
            "error": f"检查交易失败: {str(e)}"
        } 