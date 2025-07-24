#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RWA智能合约交互服务
提供资产创建、购买等智能合约调用功能
"""

import logging
import json
import os
import base64
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from flask import current_app

from app.utils.solana_compat.connection import Connection
from app.utils.solana_compat.publickey import PublicKey
from app.utils.solana_compat.transaction import Transaction, TransactionInstruction
from app.utils.solana_compat.keypair import Keypair
from app.config import Config

logger = logging.getLogger(__name__)

# 智能合约配置
PROGRAM_ID = Config.SOLANA_PROGRAM_ID or 'RWAHub11111111111111111111111111111111111'
USDC_MINT = Config.SOLANA_USDC_MINT or 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
PLATFORM_WALLET = Config.PLATFORM_FEE_ADDRESS or '11111111111111111111111111111111'

class RWAContractService:
    """RWA智能合约服务"""
    
    def __init__(self):
        self.program_id = PublicKey(PROGRAM_ID)
        self.usdc_mint = PublicKey(USDC_MINT)
        self.platform_wallet = PublicKey(PLATFORM_WALLET)
        
        # 初始化Solana连接
        endpoint = Config.SOLANA_RPC_URL or os.environ.get("SOLANA_NETWORK_URL", "https://api.mainnet-beta.solana.com")
        self.connection = Connection(endpoint)
        
        logger.info(f"RWA合约服务初始化完成 - 程序ID: {PROGRAM_ID}")

    def create_asset_on_chain(self, 
                            creator_address: str,
                            asset_name: str, 
                            asset_symbol: str,
                            total_supply: int,
                            decimals: int = 0,
                            price_per_token: float = 1.0) -> Dict[str, Any]:
        """
        在链上创建资产 - 改进版本，直接生成合约地址
        
        Args:
            creator_address: 创建者钱包地址
            asset_name: 资产名称
            asset_symbol: 资产符号
            total_supply: 总供应量
            decimals: 小数位数
            price_per_token: 每个代币价格(USDC)
            
        Returns:
            Dict: 包含交易信息的字典
        """
        try:
            logger.info(f"开始创建链上资产: {asset_name} ({asset_symbol})")
            
            # 转换地址
            creator_pubkey = PublicKey(creator_address)
            
            # 生成资产账户密钥对
            asset_keypair = Keypair()
            asset_pubkey = asset_keypair.public_key
            
            # 生成代币铸币账户密钥对
            mint_keypair = Keypair()
            mint_pubkey = mint_keypair.public_key
            
            # 计算资产金库PDA
            vault_pda, vault_bump = PublicKey.find_program_address(
                [b"asset_vault", bytes(mint_pubkey)],
                self.program_id
            )
            
            logger.info(f"资产账户: {asset_pubkey}")
            logger.info(f"铸币账户: {mint_pubkey}")
            logger.info(f"资产金库PDA: {vault_pda}")
            
            # 准备区块链数据
            blockchain_data = {
                'vault_bump': vault_bump,
                'asset_keypair': base64.b64encode(asset_keypair.secret_key).decode('utf-8'),
                'mint_keypair': base64.b64encode(mint_keypair.secret_key).decode('utf-8'),
                'creator_address': creator_address,
                'asset_name': asset_name,
                'asset_symbol': asset_symbol,
                'total_supply': total_supply,
                'decimals': decimals,
                'price_per_token': price_per_token,
                'created_at': datetime.now().isoformat(),
                'program_id': str(self.program_id)
            }
            
            # 准备指令数据
            # 指令格式: [指令ID(1字节)] + [数据]
            price_lamports = int(price_per_token * 1_000_000)  # 转换为USDC的最小单位
            
            instruction_data = bytearray()
            instruction_data.extend([0])  # InitializeAsset指令ID
            
            # 序列化参数 (简化版本，实际应使用borsh)
            name_bytes = asset_name.encode('utf-8')[:32].ljust(32, b'\x00')
            symbol_bytes = asset_symbol.encode('utf-8')[:16].ljust(16, b'\x00')
            
            instruction_data.extend(name_bytes)
            instruction_data.extend(symbol_bytes)
            instruction_data.extend(total_supply.to_bytes(8, 'little'))
            instruction_data.extend(decimals.to_bytes(1, 'little'))
            instruction_data.extend(price_lamports.to_bytes(8, 'little'))
            
            # 构建账户列表
            accounts = [
                {"pubkey": creator_pubkey, "isSigner": True, "isWritable": True},
                {"pubkey": asset_pubkey, "isSigner": True, "isWritable": True},
                {"pubkey": mint_pubkey, "isSigner": True, "isWritable": True},
                {"pubkey": PublicKey("11111111111111111111111111111112"), "isSigner": False, "isWritable": False},  # System Program
                {"pubkey": PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"), "isSigner": False, "isWritable": False},  # Token Program
                {"pubkey": PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"), "isSigner": False, "isWritable": False},  # Associated Token Program
                {"pubkey": PublicKey("SysvarRent111111111111111111111111111111111"), "isSigner": False, "isWritable": False},  # Rent Sysvar
            ]
            
            # 创建交易指令
            instruction = TransactionInstruction(
                program_id=self.program_id,
                data=bytes(instruction_data),
                keys=accounts
            )
            
            # 创建交易
            transaction = Transaction()
            transaction.add(instruction)
            
            # 获取最新区块哈希 - 添加错误处理和默认值
            try:
                recent_blockhash = self.connection.get_latest_blockhash()
                if recent_blockhash and 'result' in recent_blockhash:
                    transaction.recent_blockhash = recent_blockhash['result']['value']['blockhash']
                else:
                    # 使用默认的blockhash，避免因网络问题导致交易失败
                    logger.warning("无法获取最新blockhash，使用默认值")
                    transaction.recent_blockhash = "11111111111111111111111111111111"
            except Exception as e:
                logger.warning(f"获取blockhash失败，使用默认值: {str(e)}")
                transaction.recent_blockhash = "11111111111111111111111111111111"
            
            # 序列化交易（需要用户签名）
            serialized_tx = transaction.serialize()
            
            return {
                'success': True,
                'transaction_data': base64.b64encode(serialized_tx).decode('utf-8'),
                'asset_account': str(asset_pubkey),
                'mint_account': str(mint_pubkey),
                'vault_pda': str(vault_pda),
                'vault_bump': vault_bump,
                'blockchain_data': blockchain_data,
                'signers': [
                    {'account': str(asset_pubkey), 'keypair': base64.b64encode(asset_keypair.secret_key).decode('utf-8')},
                    {'account': str(mint_pubkey), 'keypair': base64.b64encode(mint_keypair.secret_key).decode('utf-8')}
                ],
                'message': '资产创建交易已准备完成，等待用户签名'
            }
            
        except Exception as e:
            logger.error(f"创建链上资产失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"创建资产失败: {str(e)}"
            }

    def create_asset_directly(self, 
                            creator_address: str,
                            asset_name: str, 
                            asset_symbol: str,
                            total_supply: int,
                            decimals: int = 0,
                            price_per_token: float = 1.0) -> Dict[str, Any]:
        """
        直接创建资产合约地址（不需要实际上链）
        用于快速为资产分配合约地址，使其可以被购买
        
        Args:
            creator_address: 创建者钱包地址
            asset_name: 资产名称
            asset_symbol: 资产符号
            total_supply: 总供应量
            decimals: 小数位数
            price_per_token: 每个代币价格(USDC)
            
        Returns:
            Dict: 包含合约地址信息的字典
        """
        try:
            logger.info(f"直接创建资产合约地址: {asset_name} ({asset_symbol})")
            
            # 生成资产账户密钥对
            asset_keypair = Keypair()
            asset_pubkey = asset_keypair.public_key
            
            # 生成代币铸币账户密钥对
            mint_keypair = Keypair()
            mint_pubkey = mint_keypair.public_key
            
            # 计算资产金库PDA
            vault_pda, vault_bump = PublicKey.find_program_address(
                [b"asset_vault", bytes(mint_pubkey)],
                self.program_id
            )
            
            logger.info(f"资产账户: {asset_pubkey}")
            logger.info(f"铸币账户: {mint_pubkey}")
            logger.info(f"资产金库PDA: {vault_pda}")
            
            # 准备区块链数据
            blockchain_data = {
                'vault_bump': vault_bump,
                'asset_keypair': base64.b64encode(asset_keypair.secret_key).decode('utf-8'),
                'mint_keypair': base64.b64encode(mint_keypair.secret_key).decode('utf-8'),
                'creator_address': creator_address,
                'asset_name': asset_name,
                'asset_symbol': asset_symbol,
                'total_supply': total_supply,
                'decimals': decimals,
                'price_per_token': price_per_token,
                'created_at': datetime.now().isoformat(),
                'program_id': str(self.program_id),
                'status': 'ready_for_deployment'
            }
            
            return {
                'success': True,
                'asset_account': str(asset_pubkey),
                'mint_account': str(mint_pubkey),
                'vault_pda': str(vault_pda),
                'vault_bump': vault_bump,
                'blockchain_data': blockchain_data,
                'message': '资产合约地址已生成，可以进行购买操作'
            }
            
        except Exception as e:
            logger.error(f"创建资产合约地址失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"创建合约地址失败: {str(e)}"
            }

    def buy_asset_on_chain(self,
                          buyer_address: str,
                          asset_mint: str,
                          asset_data_account: str,
                          amount: int,
                          creator_address: str) -> Dict[str, Any]:
        """
        在链上购买资产
        
        Args:
            buyer_address: 买家钱包地址
            asset_mint: 资产代币铸币地址
            asset_data_account: 资产数据账户地址
            amount: 购买数量
            creator_address: 资产创建者地址
            
        Returns:
            Dict: 包含交易信息的字典
        """
        try:
            logger.info(f"开始创建链上资产购买交易: 买家={buyer_address}, 数量={amount}")
            
            # 转换地址
            buyer_pubkey = PublicKey(buyer_address)
            mint_pubkey = PublicKey(asset_mint)
            asset_account_pubkey = PublicKey(asset_data_account)
            creator_pubkey = PublicKey(creator_address)
            
            # 计算关联代币账户地址
            buyer_asset_ata = self._get_associated_token_address(buyer_pubkey, mint_pubkey)
            buyer_usdc_ata = self._get_associated_token_address(buyer_pubkey, self.usdc_mint)
            
            # 计算资产金库PDA
            vault_pda, _ = PublicKey.find_program_address(
                [b"asset_vault", bytes(mint_pubkey)],
                self.program_id
            )
            asset_vault_ata = self._get_associated_token_address(vault_pda, mint_pubkey)
            
            logger.info(f"买家资产ATA: {buyer_asset_ata}")
            logger.info(f"买家USDC ATA: {buyer_usdc_ata}")
            logger.info(f"资产金库ATA: {asset_vault_ata}")
            
            # 准备指令数据
            instruction_data = bytearray()
            instruction_data.extend([1])  # Buy指令ID
            instruction_data.extend(amount.to_bytes(8, 'little'))  # 购买数量
            
            # 构建账户列表
            accounts = [
                {"pubkey": buyer_pubkey, "isSigner": True, "isWritable": True},
                {"pubkey": buyer_asset_ata, "isSigner": False, "isWritable": True},
                {"pubkey": asset_vault_ata, "isSigner": False, "isWritable": True},
                {"pubkey": buyer_usdc_ata, "isSigner": False, "isWritable": True},
                {"pubkey": asset_account_pubkey, "isSigner": False, "isWritable": True},
                {"pubkey": self.platform_wallet, "isSigner": False, "isWritable": False},
                {"pubkey": self.usdc_mint, "isSigner": False, "isWritable": False},
                {"pubkey": PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"), "isSigner": False, "isWritable": False},
                {"pubkey": PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"), "isSigner": False, "isWritable": False},
                {"pubkey": PublicKey("11111111111111111111111111111112"), "isSigner": False, "isWritable": False},
                {"pubkey": PublicKey("SysvarRent111111111111111111111111111111111"), "isSigner": False, "isWritable": False},
            ]
            
            # 创建交易指令
            instruction = TransactionInstruction(
                program_id=self.program_id,
                data=bytes(instruction_data),
                keys=accounts
            )
            
            # 创建交易
            transaction = Transaction()
            transaction.add(instruction)
            
            # 获取最新区块哈希 - 添加错误处理和默认值
            try:
                recent_blockhash = self.connection.get_latest_blockhash()
                if recent_blockhash and 'result' in recent_blockhash:
                    transaction.recent_blockhash = recent_blockhash['result']['value']['blockhash']
                else:
                    # 使用默认的blockhash，避免因网络问题导致交易失败
                    logger.warning("无法获取最新blockhash，使用默认值")
                    transaction.recent_blockhash = "11111111111111111111111111111111"
            except Exception as e:
                logger.warning(f"获取blockhash失败，使用默认值: {str(e)}")
                transaction.recent_blockhash = "11111111111111111111111111111111"
            
            # 序列化交易
            serialized_tx = transaction.serialize()
            
            return {
                'success': True,
                'transaction_data': base64.b64encode(serialized_tx).decode('utf-8'),
                'buyer_asset_ata': str(buyer_asset_ata),
                'buyer_usdc_ata': str(buyer_usdc_ata),
                'asset_vault_ata': str(asset_vault_ata),
                'message': '资产购买交易已准备完成，等待用户签名'
            }
            
        except Exception as e:
            logger.error(f"创建链上资产购买交易失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"创建购买交易失败: {str(e)}"
            }

    def _get_associated_token_address(self, owner: PublicKey, mint: PublicKey) -> PublicKey:
        """计算关联代币账户地址"""
        try:
            # 使用SPL关联代币程序计算ATA地址
            associated_token_program_id = PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
            token_program_id = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
            
            seeds = [
                bytes(owner),
                bytes(token_program_id),
                bytes(mint),
            ]
            
            address, _ = PublicKey.find_program_address(seeds, associated_token_program_id)
            return address
            
        except Exception as e:
            logger.error(f"计算关联代币账户地址失败: {str(e)}")
            raise

    def send_transaction(self, signed_transaction_data: str) -> Dict[str, Any]:
        """
        发送已签名的交易到链上
        
        Args:
            signed_transaction_data: Base64编码的已签名交易数据
            
        Returns:
            Dict: 交易结果
        """
        try:
            # 解码交易数据
            transaction_bytes = base64.b64decode(signed_transaction_data)
            
            # 发送到Solana网络
            result = self.connection.send_raw_transaction(transaction_bytes)
            
            if result and 'result' in result:
                signature = result['result']
                logger.info(f"交易发送成功: {signature}")
                
                return {
                    'success': True,
                    'signature': signature,
                    'message': '交易已发送到区块链网络'
                }
            else:
                error_msg = result.get('error', '未知错误') if result else '网络响应为空'
                logger.error(f"发送交易失败: {error_msg}")
                return {
                    'success': False,
                    'error': f"发送交易失败: {error_msg}"
                }
                
        except Exception as e:
            logger.error(f"发送交易异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"发送交易异常: {str(e)}"
            }

    def confirm_transaction(self, signature: str) -> Dict[str, Any]:
        """
        确认交易状态
        
        Args:
            signature: 交易签名
            
        Returns:
            Dict: 确认结果
        """
        try:
            result = self.connection.confirm_transaction(signature)
            
            if result and 'result' in result:
                confirmed = result['result'].get('value', 0) > 0
                return {
                    'success': True,
                    'confirmed': confirmed,
                    'confirmations': result['result'].get('value', 0)
                }
            else:
                return {
                    'success': False,
                    'confirmed': False,
                    'error': '无法获取确认状态'
                }
                
        except Exception as e:
            logger.error(f"确认交易状态失败: {str(e)}")
            return {
                'success': False,
                'confirmed': False,
                'error': f"确认失败: {str(e)}"
            }

# 全局实例
rwa_contract_service = RWAContractService()