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
from app.utils.solana_compat.transaction import Transaction, TransactionInstruction
from app.utils.solana_compat.tx_opts import TxOpts
from app.config import Config
from app.extensions import db
from app.models import Trade, Asset
from datetime import datetime
from spl.token.constants import TOKEN_PROGRAM_ID

# 获取日志记录器
logger = logging.getLogger(__name__)

# 通用常量
SOLANA_ENDPOINT = Config.SOLANA_RPC_URL or 'https://api.devnet.solana.com'
PROGRAM_ID = Config.SOLANA_PROGRAM_ID or 'RWAxxx111111111111111111111111111111111111'
USDC_MINT = Config.SOLANA_USDC_MINT or 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'  # Solana Devnet USDC

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
        
        # 创建真实的Solana转账交易
        from app.utils.solana_compat.publickey import PublicKey
        from app.utils.solana_compat.transaction import Transaction, TransactionInstruction
        from spl.token.constants import TOKEN_PROGRAM_ID
        
        # 创建交易
        transaction = Transaction()
        transaction.recent_blockhash = blockhash
        
        # 获取代币铸造地址
        token_mint = PublicKey(USDC_MINT)
        
        # 将from_address和to_address转换为PublicKey
        sender = PublicKey(from_address)
        recipient = PublicKey(to_address)
        
        # 创建转账指令所需的账户
        from app.utils.solana import SolanaClient
        solana_client = SolanaClient()
        
        # 获取代币账户地址
        sender_token_account = solana_client.get_token_account(sender, token_mint)
        recipient_token_account = solana_client.get_token_account(recipient, token_mint)
        
        # 将金额转换为正确的小数位数
        amount_lamports = int(amount * 1000000)  # USDC有6位小数
        
        # 创建转账指令
        # 这里使用SPL Token程序的transfer指令
        # 在真实环境中需要根据SPL Token程序的ABI来构建
        transfer_instruction_data = bytes([3]) + amount_lamports.to_bytes(8, byteorder='little')  # 3 = Transfer指令ID
        
        keys = [
            {"pubkey": sender_token_account, "isSigner": False, "isWritable": True},
            {"pubkey": recipient_token_account, "isSigner": False, "isWritable": True},
            {"pubkey": sender, "isSigner": True, "isWritable": False}
        ]
        
        transfer_instruction = TransactionInstruction(
            program_id=TOKEN_PROGRAM_ID,
            data=transfer_instruction_data,
            keys=keys
        )
        
        # 添加指令到交易
        transaction.add(transfer_instruction)
        
        # 序列化交易
        transaction_bytes = transaction.serialize()
        
        # 获取交易消息（用于签名）
        message_bytes = transaction.serialize_message()
        
        logger.info(f"已成功生成真实交易数据")
        
        return transaction_bytes, message_bytes
        
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
    这是一个后端验证方案，但仅用于确认转账请求，不实际执行转账
    
    Args:
        token_symbol (str): 代币符号
        from_address (str): 发送方地址
        to_address (str): 接收方地址
        amount (float): 转账金额
        
    Returns:
        str: 交易签名
    """
    try:
        logger.info(f"执行备用模式转账确认 - 代币: {token_symbol}, 发送方: {from_address}, 接收方: {to_address}, 金额: {amount}")
        
        # 生成一个唯一的交易ID，用于前端跟踪
        import hashlib
        
        # 创建一个唯一的种子
        seed = f"{token_symbol}:{from_address}:{to_address}:{amount}:{int(time.time())}"
        
        # 生成交易ID（非链上签名，仅用于前端UI跟踪）
        signature = hashlib.sha256(seed.encode()).hexdigest()
        
        # 创建交易记录
        from app.models import Trade, Asset
        from app.extensions import db
        
        # 查找相关资产
        asset = None
        if token_symbol == 'USDC':
            # 尝试从to_address判断是转账给平台还是资产创建者
            if to_address == "8mYGpVRUoKgZyqRUNQzGN1iQwKRXtA1bMDTnj8YX1bYM":
                # 如果是平台费，查找资产信息可能在另一个转账中
                logger.info("此转账为平台费，不关联具体资产")
            else:
                # 查找资产创建者地址匹配的资产
                assets = Asset.query.filter_by(creator_address=to_address).all()
                if assets:
                    asset = assets[0]  # 取第一个匹配的资产
                    logger.info(f"找到匹配的资产: {asset.token_symbol}")
        
        # 记录交易到数据库
        trade = Trade(
            wallet_address=from_address,
            asset_id=asset.id if asset else None,
            amount=amount,
            price=asset.token_price if asset else 0,
            tx_hash=signature,
            status='pending',  # 初始状态为pending
            token_amount=amount / (asset.token_price if asset and asset.token_price > 0 else 1)
        )
        db.session.add(trade)
        db.session.commit()
        
        logger.info(f"备用模式交易记录已创建 - 交易ID: {trade.id}, 签名: {signature}")
        
        return signature
        
    except Exception as e:
        logger.error(f"备用转账确认失败: {str(e)}")
        raise Exception(f"备用转账确认失败: {str(e)}")

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
        dict: 交易数据，包含已经base58编码的交易信息
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
        
        # 直接返回base58编码的交易消息
        import base58
        
        # 序列化交易消息
        message_bytes = transaction.serialize_message()
        
        # 使用base58编码 
        base58_message = base58.b58encode(message_bytes).decode('utf-8')
        
        logger.info(f"已生成base58格式的交易消息")
        
        # 返回交易数据，包含base58编码的消息
        return {
            "success": True,
            "serialized_transaction": base58_message,
            "trade_id": trade_id
        }
        
    except Exception as e:
        logger.error(f"准备Solana交易失败: {str(e)}")
        return {
            "success": False,
            "error": f"准备交易失败: {str(e)}"
        }

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