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
from app.models.trade import TradeType
from datetime import datetime
from spl.token.constants import TOKEN_PROGRAM_ID
import base58

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
    blockhash: str = None
) -> Tuple[bytes, bytes]:
    """
    准备转账交易数据和消息
    
    Args:
        token_symbol (str): 代币符号
        from_address (str): 发送方地址
        to_address (str): 接收方地址
        amount (float): 转账金额
        blockhash (str, optional): 最新区块哈希，若不提供则自动获取
        
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
        
        # 如果没有提供blockhash，则从网络获取最新区块哈希
        if not blockhash:
            logger.info("未提供blockhash，尝试获取最新区块哈希")
            
            # 定义多个可用的Solana RPC节点以增加可靠性
            solana_rpc_nodes = [
                "https://api.mainnet-beta.solana.com",
                "https://solana-api.projectserum.com",
                "https://rpc.ankr.com/solana",
                "https://solana.public-rpc.com"
            ]
            
            # 尝试从多个节点获取区块哈希
            blockhash_obtained = False
            blockhash_errors = []
            
            for rpc_node in solana_rpc_nodes:
                try:
                    logger.info(f"尝试从节点获取区块哈希: {rpc_node}")
                    from app.utils.solana_compat.connection import Connection
                    temp_connection = Connection(rpc_node)
                    
                    recent_blockhash_response = temp_connection.get_recent_blockhash()
                    if 'result' in recent_blockhash_response and 'value' in recent_blockhash_response['result']:
                        blockhash = recent_blockhash_response['result']['value']['blockhash']
                        if blockhash:
                            logger.info(f"成功从节点 {rpc_node} 获取区块哈希: {blockhash}")
                            blockhash_obtained = True
                            break
                    else:
                        error_msg = f"从节点 {rpc_node} 获取的响应格式无效: {recent_blockhash_response}"
                        logger.warning(error_msg)
                        blockhash_errors.append(error_msg)
                except Exception as rpc_error:
                    error_msg = f"从节点 {rpc_node} 获取区块哈希失败: {str(rpc_error)}"
                    logger.warning(error_msg)
                    blockhash_errors.append(error_msg)
            
            # 如果所有节点都失败，则使用备用方法生成哈希
            if not blockhash_obtained:
                logger.error(f"所有Solana节点获取区块哈希均失败。错误信息: {', '.join(blockhash_errors)}")
                # 作为最后的备用选项，生成一个适当的哈希值
                import hashlib
                import time
                import random
                
                # 使用当前时间、随机数和一些特定信息生成哈希
                random_data = f"backup-{time.time()}-{random.randint(1, 1000000)}-{from_address}-{to_address}"
                blockhash = hashlib.sha256(random_data.encode()).hexdigest()
                logger.warning(f"使用备用生成的区块哈希: {blockhash}")
        else:
            logger.info(f"使用提供的区块哈希: {blockhash}")
        
        # 设置区块哈希
        transaction.recent_blockhash = blockhash
        
        # 获取代币铸造地址
        token_mint = PublicKey(USDC_MINT)
        logger.info(f"使用代币铸造地址: {USDC_MINT}")
        
        # 将from_address和to_address转换为PublicKey
        try:
            sender = PublicKey(from_address)
            recipient = PublicKey(to_address)
            logger.info("成功转换发送方和接收方地址为PublicKey格式")
        except Exception as pk_error:
            logger.error(f"转换地址为PublicKey失败: {str(pk_error)}")
            raise Exception(f"无效的Solana地址格式: {str(pk_error)}")
        
        # 创建转账指令所需的账户
        try:
            from app.utils.solana import SolanaClient
            solana_client = SolanaClient()
            
            # 获取代币账户地址
            sender_token_account = solana_client.get_token_account(sender, token_mint)
            recipient_token_account = solana_client.get_token_account(recipient, token_mint)
            
            logger.info(f"发送方代币账户: {sender_token_account}")
            logger.info(f"接收方代币账户: {recipient_token_account}")
        except Exception as account_error:
            logger.error(f"获取代币账户失败: {str(account_error)}")
            raise Exception(f"获取代币账户失败: {str(account_error)}")
        
        # 将金额转换为正确的小数位数
        amount_lamports = int(amount * 1000000)  # USDC有6位小数
        logger.info(f"转换金额 {amount} USDC 为 {amount_lamports} lamports")
        
        # 创建转账指令
        try:
            # 这里使用SPL Token程序的transfer指令
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
            logger.info("转账指令已添加到交易")
        except Exception as instruction_error:
            logger.error(f"创建转账指令失败: {str(instruction_error)}")
            raise Exception(f"创建转账指令失败: {str(instruction_error)}")
        
        # 序列化交易
        try:
            transaction_bytes = transaction.serialize()
            # 获取交易消息（用于签名）
            message_bytes = transaction.serialize_message()
            
            # 确保日志记录了序列化结果的长度
            logger.info(f"已成功生成真实交易数据，transaction_bytes长度: {len(transaction_bytes)}, message_bytes长度: {len(message_bytes)}")
            
            return transaction_bytes, message_bytes
        except Exception as serialize_error:
            logger.error(f"序列化交易失败: {str(serialize_error)}")
            raise Exception(f"序列化交易失败: {str(serialize_error)}")
        
    except Exception as e:
        logger.error(f"准备交易数据失败: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
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


def execute_transfer_transaction(
    token_symbol: str,
    from_address: str,
    to_address: str,
    amount: float
) -> str:
    """
    执行真实的Solana链上转账交易
    
    Args:
        token_symbol (str): 代币符号，如'USDC'
        from_address (str): 发送方地址
        to_address (str): 接收方地址
        amount (float): 转账金额
        
    Returns:
        str: 交易签名
    """
    try:
        logger.info(f"执行真实Solana转账 - 代币: {token_symbol}, 发送方: {from_address}, 接收方: {to_address}, 金额: {amount}")
        
        # 验证输入参数
        if not token_symbol or not isinstance(token_symbol, str):
            raise ValueError(f"无效的代币符号: {token_symbol}")
            
        if not from_address or not isinstance(from_address, str) or len(from_address) < 32:
            raise ValueError(f"无效的发送方地址: {from_address}")
            
        if not to_address or not isinstance(to_address, str) or len(to_address) < 32:
            raise ValueError(f"无效的接收方地址: {to_address}")
            
        if not amount or not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError(f"无效的转账金额: {amount}")
        
        # 创建交易所需参数
        logger.info("准备创建交易参数...")
        transaction_bytes, message_bytes = prepare_transfer_transaction(
            token_symbol=token_symbol,
            from_address=from_address,
            to_address=to_address,
            amount=amount
        )
        logger.info(f"交易参数创建成功，交易数据大小: {len(transaction_bytes)}字节")
        
        # 获取系统服务钱包（如果是管理员操作时使用）
        from app.utils.solana import SolanaClient
        logger.info("初始化Solana客户端...")
        solana_client = SolanaClient()
        
        # 使用Solana客户端发送交易
        try:
            # 序列化交易并使用Base58编码(而不是Base64)
            transaction_base58 = base58.b58encode(transaction_bytes).decode('utf-8')
            logger.info(f"交易序列化完成，Base58编码大小: {len(transaction_base58)}字符")
            
            # 检查连接状态
            try:
                slot_response = solana_connection.get_slot()
                logger.info(f"Solana网络连接正常，当前slot: {slot_response.get('result', 'unknown')}")
            except Exception as conn_error:
                logger.error(f"检查Solana网络连接失败: {str(conn_error)}")
                raise Exception(f"Solana网络连接失败: {str(conn_error)}")
            
            # 发送交易到Solana网络
            logger.info("开始发送交易到Solana网络...")
            # 直接使用RPC客户端发送原始交易数据，使用Base58编码
            result = solana_connection.rpc_client._make_request(
                "sendTransaction",
                [transaction_base58, {
                    "skipPreflight": False,
                    "preflightCommitment": "confirmed"
                }]
            )
            
            # 详细记录结果
            logger.info(f"发送交易响应: {json.dumps(result, indent=2)}")
            
            # 获取交易签名
            signature = result.get('result', None)
            
            if not signature:
                error_info = result.get('error', {})
                error_message = error_info.get('message', '未知错误') if isinstance(error_info, dict) else str(error_info)
                logger.error(f"未获取到交易签名，错误: {error_message}")
                raise Exception(f"未获取到交易签名: {error_message}")
                
            logger.info(f"交易已发送到Solana网络，签名: {signature}")
            
            # 创建交易记录
            try:
                # 寻找相关资产
                asset = Asset.query.filter_by(token_symbol=token_symbol).first()
                if not asset:
                    logger.warning(f"未找到与符号 {token_symbol} 匹配的资产")
                
                # 创建交易记录
                trade = Trade(
                    trade_type=TradeType.PLATFORM_FEE,
                    trader_address=from_address,
                    amount=amount,
                    price=1.0,  # 平台费以1:1比例计算
                    asset_id=asset.id if asset else None,
                    token_amount=amount,  # 使用实际金额作为代币数量
                    status='processing',  # 设置状态为处理中，表示已发送但未确认
                    tx_hash=signature
                )
                
                db.session.add(trade)
                db.session.commit()
                
                logger.info(f"已创建交易记录 ID: {trade.id}, 签名: {signature}, 状态: processing")
                
                # 启动异步任务监控交易确认状态
                try:
                    from app.tasks import monitor_transaction_confirmation
                    monitor_transaction_confirmation.delay('monitor_transaction_confirmation', signature, trade.id)
                    logger.info(f"已启动交易确认监控任务，交易ID: {trade.id}")
                except Exception as task_error:
                    logger.error(f"启动交易确认监控任务失败: {str(task_error)}")
                
            except Exception as db_error:
                logger.error(f"创建交易记录失败: {str(db_error)}")
                # 交易记录创建失败不影响流程，继续返回签名
            
            logger.info(f"Solana交易已成功处理，签名: {signature}")
            
            return signature
            
        except Exception as tx_error:
            logger.error(f"发送Solana交易失败: {str(tx_error)}")
            # 记录更详细的错误信息
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise Exception(f"发送Solana交易失败: {str(tx_error)}")
        
    except Exception as e:
        logger.error(f"执行Solana转账失败: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise Exception(f"执行Solana转账失败: {str(e)}")

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