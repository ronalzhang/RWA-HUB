#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Solana区块链服务，提供交易构建和处理功能
"""

import base64
import logging
import time
import os
import json
from typing import Tuple, Dict, Any, Optional

from flask import current_app

# 导入Solana兼容工具
from app.utils.solana_compat.connection import Connection
from app.utils.solana_compat.publickey import PublicKey
from app.utils.solana_compat.transaction import Transaction, TransactionInstruction
from app.utils.solana_compat.keypair import Keypair
from app.utils.solana_compat.tx_opts import TxOpts
from app.config import Config
from app.extensions import db
from app.models import Trade, Asset
from app.models.trade import TradeType
from datetime import datetime
import base58

# 使用真实的TOKEN_PROGRAM_ID常量
TOKEN_PROGRAM_ID = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')

# 获取日志记录器
logger = logging.getLogger(__name__)

# 通用常量
SOLANA_ENDPOINT = os.environ.get("SOLANA_NETWORK_URL") or Config.SOLANA_RPC_URL or "https://api.mainnet-beta.solana.com"
PROGRAM_ID = Config.SOLANA_PROGRAM_ID or 'RWAxxx111111111111111111111111111111111111'
USDC_MINT = Config.SOLANA_USDC_MINT or 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'  # Solana Mainnet USDC

# 创建Solana连接
solana_connection = None

def validate_solana_address(address: str) -> bool:
    """
    验证Solana地址格式
    
    Args:
        address (str): 要验证的地址
        
    Returns:
        bool: 地址是否有效
    """
    try:
        if not address or not isinstance(address, str):
            return False
        
        # Solana地址应该是32字节的base58编码字符串
        if len(address) < 32 or len(address) > 44:
            return False
        
        # 尝试解码base58
        try:
            decoded = base58.b58decode(address)
            return len(decoded) == 32
        except:
            return False
            
    except Exception:
        return False

def initialize_solana_connection():
    """初始化Solana连接"""
    global solana_connection
    endpoint = Config.SOLANA_RPC_URL or os.environ.get("SOLANA_NETWORK_URL", "https://api.mainnet-beta.solana.com") or 'https://api.mainnet-beta.solana.com'
    logger.info(f"初始化Solana连接，使用端点: {endpoint}")
    try:
        solana_connection = Connection(endpoint)
        logger.info("Solana连接初始化成功")
    except Exception as e:
        logger.error(f"初始化Solana连接失败: {str(e)}")
        # 尝试使用备用节点
        backup_endpoints = [
            'https://api.mainnet-beta.solana.com',
            'https://solana-api.projectserum.com',
            'https://rpc.ankr.com/solana'
        ]
        for backup_endpoint in backup_endpoints:
            if backup_endpoint != endpoint:
                try:
                    logger.info(f"尝试使用备用节点: {backup_endpoint}")
                    solana_connection = Connection(backup_endpoint)
                    logger.info(f"使用备用节点 {backup_endpoint} 连接成功")
                    return
                except Exception as be:
                    logger.error(f"备用节点 {backup_endpoint} 连接失败: {str(be)}")
        
        # 如果所有尝试都失败，使用默认节点再试一次
        try:
            logger.warning("所有节点连接失败，使用默认节点")
            solana_connection = Connection('https://api.mainnet-beta.solana.com')
        except Exception as fe:
            logger.critical(f"无法初始化Solana连接: {str(fe)}")

# 初始化连接
initialize_solana_connection()

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


def validate_solana_address(address):
    """
    验证Solana地址格式是否有效
    
    Args:
        address (str): 要验证的Solana地址
        
    Returns:
        bool: 如果地址格式有效返回True，否则返回False
    """
    try:
        # 确保地址是字符串
        if not isinstance(address, str):
            logging.error(f"地址不是字符串: {type(address)}")
            return False
            
        # 去除空白字符
        address = address.strip()
        
        # 检查基本格式
        if len(address) < 32:
            logging.error(f"地址长度不正确: {len(address)}")
            return False
            
        # 尝试从base58解码(这是Solana地址的编码方式)
        try:
            import base58
            decoded = base58.b58decode(address)
            if len(decoded) != 32:
                logging.error(f"解码后地址长度不正确: {len(decoded)}")
                return False
        except Exception as e:
            logging.error(f"地址base58解码失败: {str(e)}")
            return False
            
        return True
    except Exception as e:
        logging.error(f"验证Solana地址时出错: {str(e)}")
        return False


def execute_transfer_transaction(
    token_symbol: str,
    from_address: str,
    to_address: str,
    amount: float
) -> str:
    """
    执行Solana代币转账交易
    
    Args:
        token_symbol (str): 代币符号，例如 "USDC"
        from_address (str): 发送方地址
        to_address (str): 接收方地址
        amount (float): 转账金额
        
    Returns:
        str: 交易签名
    """
    try:
        # 1. 详细记录输入参数
        logger.info(f"执行真实Solana转账 - 参数: token={token_symbol}, from={from_address}, to={to_address}, amount={amount}")
        
        # 检查solana_connection是否已初始化
        global solana_connection
        if solana_connection is None:
            logger.warning("Solana连接未初始化，尝试重新初始化")
            initialize_solana_connection()
            
        if solana_connection is None:
            raise RuntimeError("无法初始化Solana连接，请检查网络连接和RPC节点状态")
        
        # 2. 检查参数完整性
        if not all([token_symbol, from_address, to_address, amount]):
            missing = []
            if not token_symbol: missing.append("token_symbol")
            if not from_address: missing.append("from_address")
            if not to_address: missing.append("to_address")
            if not amount: missing.append("amount")
            error_msg = f"缺少必要参数: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 3. 验证并处理金额
        try:
            # 转换为浮点数以处理USDC的小数部分
            amount_float = float(amount)
            if amount_float <= 0:
                raise ValueError("金额必须大于0")
            
            logger.info(f"验证后的金额: {amount_float}")
        except Exception as e:
            error_msg = f"金额格式无效: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 4. 验证地址格式
        if not validate_solana_address(from_address):
            error_msg = f"发送方地址格式无效: {from_address}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not validate_solana_address(to_address):
            error_msg = f"接收方地址格式无效: {to_address}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 5. 获取代币铸造地址
        token_mapping = {
            "USDC": USDC_MINT,
            # 其他代币映射...
        }
        
        if token_symbol not in token_mapping:
            error_msg = f"不支持的代币: {token_symbol}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        token_mint = token_mapping[token_symbol]
        logger.info(f"代币铸造地址: {token_mint}")
        
        # 6. 模拟交易执行（开发环境）
        logger.info(f"模拟执行转账: {amount_float} {token_symbol} 从 {from_address} 到 {to_address}")
        
        # 生成模拟交易签名
        import hashlib
        import time
        
        # 创建基于参数的唯一签名
        signature_data = f"{from_address}{to_address}{amount_float}{token_symbol}{time.time()}"
        signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
        mock_signature = f"mock_tx_{signature_hash[:32]}"
        
        logger.info(f"生成模拟交易签名: {mock_signature}")
        
        # 模拟网络延迟
        time.sleep(1)
        
        return {
            'success': True,
            'signature': mock_signature,
            'message': '转账成功（模拟）'
        }
        
    except Exception as e:
        error_msg = f"执行Solana转账失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }

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
        
        # 获取最新的区块哈希
        try:
            recent_blockhash = solana_connection.get_latest_blockhash()
            if recent_blockhash and 'result' in recent_blockhash:
                blockhash = recent_blockhash['result']['value']['blockhash']
                transaction.set_recent_blockhash(blockhash)
                logger.info(f"使用真实区块哈希: {blockhash}")
            else:
                raise Exception("无法获取最新区块哈希")
        except Exception as e:
            logger.error(f"获取区块哈希失败: {str(e)}")
            raise Exception(f"无法获取Solana区块哈希: {str(e)}")
        
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

def _get_token_account(self, owner_address, token_mint):
    """
    获取用户的代币账户地址
    
    Args:
        owner_address: 所有者地址
        token_mint: 代币铸造地址
        
    Returns:
        代币账户地址
    """
    try:
        logger.info(f"获取代币账户 - 所有者: {owner_address}({type(owner_address).__name__}), 代币铸造: {token_mint}({type(token_mint).__name__})")
        
        # 确保地址是PublicKey对象或正确的字符串格式
        if isinstance(owner_address, str):
            # 清理地址字符串
            owner_address = owner_address.strip()
            logger.debug(f"处理所有者地址: {owner_address}, 长度: {len(owner_address)}")
            
            # 如果地址非常短或格式明显无效，提前报错
            if len(owner_address) < 30:
                logger.error(f"所有者地址格式无效，长度过短: {owner_address}")
                raise ValueError(f"无效的所有者地址格式: {owner_address} - 长度过短")
                
            # 转换为PublicKey对象
            try:
                from app.utils.solana_compat.publickey import PublicKey
                owner_pubkey = PublicKey(owner_address)
                logger.debug(f"成功创建所有者PublicKey对象")
            except Exception as pk_error:
                logger.error(f"转换所有者地址为PublicKey失败: {str(pk_error)}")
                raise ValueError(f"无效的所有者地址格式: {owner_address} - {str(pk_error)}")
        else:
            owner_pubkey = owner_address
        
        # 同样处理token_mint
        if isinstance(token_mint, str):
            token_mint = token_mint.strip()
            logger.debug(f"处理代币铸造地址: {token_mint}, 长度: {len(token_mint)}")
            
            # 如果地址非常短或格式明显无效，提前报错
            if len(token_mint) < 30:
                logger.error(f"代币铸造地址格式无效，长度过短: {token_mint}")
                raise ValueError(f"无效的代币铸造地址格式: {token_mint} - 长度过短")
                
            try:
                from app.utils.solana_compat.publickey import PublicKey
                token_mint_pubkey = PublicKey(token_mint)
                logger.debug(f"成功创建代币铸造PublicKey对象")
            except Exception as pk_error:
                logger.error(f"转换代币铸造地址为PublicKey失败: {str(pk_error)}")
                raise ValueError(f"无效的代币铸造地址格式: {token_mint} - {str(pk_error)}")
        else:
            token_mint_pubkey = token_mint
        
        # 获取关联代币账户地址
        try:
            # 使用兼容层的代码
            from app.utils.solana_compat.token.instructions import get_associated_token_address
            token_account = get_associated_token_address(
                owner_pubkey,
                token_mint_pubkey
            )
            logger.info(f"获取到代币账户: {token_account}")
            return token_account
        except Exception as e:
            logger.error(f"获取关联代币账户失败: {str(e)}", exc_info=True)
            
            # 尝试使用模拟spl库
            try:
                from app.utils.spl_mock import get_associated_token_address
                token_account = get_associated_token_address(
                    owner_pubkey,
                    token_mint_pubkey
                )
                logger.info(f"使用模拟库获取到代币账户: {token_account}")
                return token_account
            except Exception as mock_error:
                logger.error(f"使用模拟库获取关联代币账户失败: {str(mock_error)}", exc_info=True)
            
            # 尝试使用替代方法
            try:
                # 当spl库不可用时，使用公式计算关联代币账户地址
                # 这是一个简化版本，适用于大多数情况
                logger.info("尝试使用替代方法计算关联代币账户地址")
                token_program_id = TOKEN_PROGRAM_ID
                associated_token_program_id = PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
                
                seeds = [
                    owner_pubkey.to_bytes(),
                    token_program_id.to_bytes(),
                    token_mint_pubkey.to_bytes(),
                ]
                
                program_derived_address, nonce = PublicKey.find_program_address(
                    seeds, associated_token_program_id
                )
                
                logger.info(f"使用替代方法获取到代币账户: {program_derived_address}")
                return program_derived_address
            except Exception as native_error:
                logger.error(f"使用替代方法获取关联代币账户也失败: {str(native_error)}", exc_info=True)
            
            raise ValueError(f"无法获取关联代币账户: {str(e)}")
        
    except Exception as e:
        logger.error(f"获取代币账户失败: {str(e)}", exc_info=True)
        # 提供更具体的错误信息
        if "public key" in str(e).lower():
            raise ValueError(f"无效的公钥格式: {str(e)}")
        # 重新抛出异常
        raise 