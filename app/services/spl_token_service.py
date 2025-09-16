import logging
import time
import json
import base64
from typing import Dict, Optional, Tuple
from decimal import Decimal
from flask import current_app

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import create_account, CreateAccountParams
from solders.instruction import Instruction
from spl.token.instructions import (
    initialize_mint, mint_to, create_associated_token_account,
    get_associated_token_address, InitializeMintParams, MintToParams
)
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from solders.transaction import Transaction
from solders.message import Message

from app.extensions import db
from app.models import Asset
from app.blockchain.solana_service import get_solana_client, get_latest_blockhash_with_cache
from app.utils.crypto_manager import CryptoManager

logger = logging.getLogger(__name__)


class SplTokenService:
    """
    SPL Token 服务类
    负责创建、管理和操作真正的Solana SPL代币
    """

    # SPL Token创建状态枚举
    class CreationStatus:
        PENDING = 0      # 待创建
        CREATING = 1     # 创建中
        COMPLETED = 2    # 创建完成
        FAILED = 3       # 创建失败

    @staticmethod
    def create_asset_token(asset_id: int, platform_keypair: Optional[Keypair] = None) -> Dict:
        """
        为资产创建真正的SPL Token

        Args:
            asset_id: 资产ID
            platform_keypair: 平台私钥对，用于支付创建费用

        Returns:
            dict: 创建结果，包含mint地址、交易哈希等信息
        """
        operation_id = f"create_token_{asset_id}_{int(time.time())}"
        logger.info(f"[{operation_id}] 开始为资产ID {asset_id} 创建SPL Token")

        try:
            # 1. 查询资产信息
            asset = Asset.query.get(asset_id)
            if not asset:
                return {
                    'success': False,
                    'error': 'ASSET_NOT_FOUND',
                    'message': f'资产ID {asset_id} 不存在'
                }

            # 检查是否已经创建过SPL Token
            if hasattr(asset, 'spl_mint_address') and asset.spl_mint_address:
                return {
                    'success': False,
                    'error': 'TOKEN_ALREADY_EXISTS',
                    'message': f'资产 {asset.token_symbol} 已经有对应的SPL Token',
                    'mint_address': asset.spl_mint_address
                }

            logger.info(f"[{operation_id}] 找到资产: {asset.token_symbol}, 总供应量: {asset.token_supply}")

            # 2. 生成Token mint keypair
            mint_keypair = Keypair()
            mint_pubkey = mint_keypair.pubkey()
            mint_address = str(mint_pubkey)

            logger.info(f"[{operation_id}] 生成Mint地址: {mint_address}")

            # 3. 生成mint权限keypair（平台控制）
            mint_authority_keypair = Keypair()
            mint_authority_pubkey = mint_authority_keypair.pubkey()

            # 4. 获取平台支付keypair
            if not platform_keypair:
                platform_keypair = SplTokenService._get_platform_keypair()
                if not platform_keypair:
                    return {
                        'success': False,
                        'error': 'PLATFORM_KEYPAIR_ERROR',
                        'message': '无法获取平台私钥，请检查配置'
                    }

            platform_pubkey = platform_keypair.pubkey()

            # 5. 获取Solana客户端和最新区块哈希
            client = get_solana_client()
            recent_blockhash = get_latest_blockhash_with_cache()

            # 6. 计算所需的账户租金
            mint_account_space = 82  # SPL Token Mint账户大小
            mint_rent = client.get_minimum_balance_for_rent_exemption(mint_account_space).value

            logger.info(f"[{operation_id}] Mint账户租金: {mint_rent} lamports")

            # 7. 创建交易指令
            instructions = []

            # 创建mint账户指令
            create_account_params = CreateAccountParams(
                from_pubkey=platform_pubkey,
                to_pubkey=mint_pubkey,
                lamports=mint_rent,
                space=mint_account_space,
                owner=TOKEN_PROGRAM_ID
            )
            instructions.append(create_account(create_account_params))

            # 初始化mint指令
            decimals = 0  # 资产代币使用整数，不使用小数
            initialize_mint_params = InitializeMintParams(
                program_id=TOKEN_PROGRAM_ID,
                mint=mint_pubkey,
                decimals=decimals,
                mint_authority=mint_authority_pubkey,
                freeze_authority=mint_authority_pubkey  # 暂时设置相同权限
            )
            instructions.append(initialize_mint(initialize_mint_params))

            logger.info(f"[{operation_id}] 创建了 {len(instructions)} 个指令")

            # 8. 构建并签名交易
            message = Message.new_with_blockhash(
                instructions,
                platform_pubkey,
                recent_blockhash
            )
            transaction = Transaction.new_unsigned(message)

            # 签名交易（需要平台密钥和mint密钥）
            transaction.sign([platform_keypair, mint_keypair], recent_blockhash)

            logger.info(f"[{operation_id}] 交易已签名，准备发送")

            # 9. 发送交易
            tx_response = client.send_raw_transaction(bytes(transaction))
            tx_hash = str(tx_response.value)

            logger.info(f"[{operation_id}] 交易已发送: {tx_hash}")

            # 10. 等待确认
            confirmation = client.confirm_transaction(tx_hash)
            if confirmation.value.err:
                logger.error(f"[{operation_id}] 交易确认失败: {confirmation.value.err}")
                return {
                    'success': False,
                    'error': 'TRANSACTION_FAILED',
                    'message': f'SPL Token创建交易失败: {confirmation.value.err}',
                    'tx_hash': tx_hash
                }

            logger.info(f"[{operation_id}] 交易确认成功")

            # 11. 更新数据库
            try:
                # 加密存储mint权限私钥
                encrypted_mint_authority = CryptoManager.encrypt_data(
                    bytes(mint_authority_keypair).hex()
                )

                # 更新资产记录
                asset.spl_mint_address = mint_address
                asset.mint_authority_keypair = encrypted_mint_authority
                asset.spl_creation_status = SplTokenService.CreationStatus.COMPLETED
                asset.spl_creation_tx_hash = tx_hash

                db.session.commit()
                logger.info(f"[{operation_id}] 数据库更新成功")

            except Exception as db_error:
                logger.error(f"[{operation_id}] 数据库更新失败: {db_error}")
                db.session.rollback()
                return {
                    'success': False,
                    'error': 'DATABASE_ERROR',
                    'message': f'SPL Token创建成功但数据库更新失败: {str(db_error)}',
                    'mint_address': mint_address,
                    'tx_hash': tx_hash
                }

            # 12. 返回成功结果
            return {
                'success': True,
                'message': f'SPL Token创建成功: {asset.token_symbol}',
                'data': {
                    'mint_address': mint_address,
                    'mint_authority': str(mint_authority_pubkey),
                    'tx_hash': tx_hash,
                    'decimals': decimals,
                    'total_supply': asset.token_supply,
                    'asset_symbol': asset.token_symbol
                }
            }

        except Exception as e:
            logger.error(f"[{operation_id}] SPL Token创建失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'CREATION_ERROR',
                'message': f'SPL Token创建失败: {str(e)}'
            }

    @staticmethod
    def mint_tokens_to_user(
        mint_address: str,
        user_address: str,
        amount: int,
        asset_id: int
    ) -> Dict:
        """
        Mint代币给用户

        Args:
            mint_address: Token mint地址
            user_address: 用户钱包地址
            amount: mint数量
            asset_id: 资产ID（用于获取mint权限）

        Returns:
            dict: mint结果
        """
        operation_id = f"mint_{mint_address[:8]}_{user_address[:8]}_{int(time.time())}"
        logger.info(f"[{operation_id}] 开始mint {amount} 个代币给用户 {user_address}")

        try:
            # 1. 获取资产信息和mint权限
            asset = Asset.query.get(asset_id)
            if not asset or not asset.mint_authority_keypair:
                return {
                    'success': False,
                    'error': 'MINT_AUTHORITY_ERROR',
                    'message': '无法获取mint权限，请检查资产配置'
                }

            # 2. 解密mint权限私钥
            try:
                encrypted_mint_authority = asset.mint_authority_keypair
                mint_authority_hex = CryptoManager.decrypt_data(encrypted_mint_authority)
                mint_authority_keypair = Keypair.from_bytes(bytes.fromhex(mint_authority_hex))
            except Exception as e:
                return {
                    'success': False,
                    'error': 'DECRYPT_ERROR',
                    'message': f'解密mint权限失败: {str(e)}'
                }

            # 3. 获取必要的公钥
            mint_pubkey = Pubkey.from_string(mint_address)
            user_pubkey = Pubkey.from_string(user_address)
            mint_authority_pubkey = mint_authority_keypair.pubkey()

            # 4. 获取用户的关联代币账户地址
            user_token_account = get_associated_token_address(user_pubkey, mint_pubkey)

            # 5. 获取平台keypair（支付交易费用）
            platform_keypair = SplTokenService._get_platform_keypair()
            if not platform_keypair:
                return {
                    'success': False,
                    'error': 'PLATFORM_KEYPAIR_ERROR',
                    'message': '无法获取平台私钥'
                }

            # 6. 检查用户代币账户是否存在
            client = get_solana_client()
            account_info = client.get_account_info(user_token_account)

            instructions = []

            # 如果用户代币账户不存在，先创建
            if not account_info.value:
                logger.info(f"[{operation_id}] 创建用户代币账户: {user_token_account}")
                create_ata_instruction = create_associated_token_account(
                    payer=platform_keypair.pubkey(),
                    owner=user_pubkey,
                    mint=mint_pubkey
                )
                instructions.append(create_ata_instruction)

            # 7. 创建mint指令
            mint_params = MintToParams(
                program_id=TOKEN_PROGRAM_ID,
                mint=mint_pubkey,
                dest=user_token_account,
                mint_authority=mint_authority_pubkey,
                amount=amount  # 直接使用整数，因为decimals=0
            )
            mint_instruction = mint_to(mint_params)
            instructions.append(mint_instruction)

            logger.info(f"[{operation_id}] 创建了 {len(instructions)} 个指令")

            # 8. 构建和发送交易
            recent_blockhash = get_latest_blockhash_with_cache()
            message = Message.new_with_blockhash(
                instructions,
                platform_keypair.pubkey(),
                recent_blockhash
            )
            transaction = Transaction.new_unsigned(message)

            # 签名（平台支付费用，mint权限执行mint）
            transaction.sign([platform_keypair, mint_authority_keypair], recent_blockhash)

            # 发送交易
            tx_response = client.send_raw_transaction(bytes(transaction))
            tx_hash = str(tx_response.value)

            logger.info(f"[{operation_id}] Mint交易已发送: {tx_hash}")

            # 9. 等待确认
            confirmation = client.confirm_transaction(tx_hash)
            if confirmation.value.err:
                logger.error(f"[{operation_id}] Mint交易确认失败: {confirmation.value.err}")
                return {
                    'success': False,
                    'error': 'MINT_TRANSACTION_FAILED',
                    'message': f'Mint交易失败: {confirmation.value.err}',
                    'tx_hash': tx_hash
                }

            logger.info(f"[{operation_id}] Mint交易确认成功")

            return {
                'success': True,
                'message': f'成功mint {amount} 个代币给用户',
                'data': {
                    'mint_address': mint_address,
                    'user_address': user_address,
                    'user_token_account': str(user_token_account),
                    'amount': amount,
                    'tx_hash': tx_hash
                }
            }

        except Exception as e:
            logger.error(f"[{operation_id}] Mint代币失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'MINT_ERROR',
                'message': f'Mint代币失败: {str(e)}'
            }

    @staticmethod
    def get_token_supply(mint_address: str) -> Dict:
        """
        获取代币的当前供应量

        Args:
            mint_address: Token mint地址

        Returns:
            dict: 包含供应量信息的结果
        """
        try:
            client = get_solana_client()
            mint_pubkey = Pubkey.from_string(mint_address)

            response = client.get_token_supply(mint_pubkey)
            if response.value:
                return {
                    'success': True,
                    'data': {
                        'total_supply': int(response.value.amount),
                        'decimals': response.value.decimals
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'TOKEN_NOT_FOUND',
                    'message': f'未找到mint地址 {mint_address} 对应的代币'
                }

        except Exception as e:
            logger.error(f"获取代币供应量失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'SUPPLY_QUERY_ERROR',
                'message': f'查询代币供应量失败: {str(e)}'
            }

    @staticmethod
    def get_user_token_balance(user_address: str, mint_address: str) -> Dict:
        """
        获取用户的代币余额

        Args:
            user_address: 用户钱包地址
            mint_address: Token mint地址

        Returns:
            dict: 用户代币余额信息
        """
        try:
            client = get_solana_client()
            user_pubkey = Pubkey.from_string(user_address)
            mint_pubkey = Pubkey.from_string(mint_address)

            # 获取用户的关联代币账户
            user_token_account = get_associated_token_address(user_pubkey, mint_pubkey)

            # 查询余额
            response = client.get_token_account_balance(user_token_account)
            if response.value:
                return {
                    'success': True,
                    'data': {
                        'balance': int(response.value.amount),
                        'decimals': response.value.decimals,
                        'token_account': str(user_token_account)
                    }
                }
            else:
                return {
                    'success': True,
                    'data': {
                        'balance': 0,
                        'decimals': 0,
                        'token_account': str(user_token_account)
                    }
                }

        except Exception as e:
            logger.error(f"获取用户代币余额失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'BALANCE_QUERY_ERROR',
                'message': f'查询用户代币余额失败: {str(e)}'
            }

    @staticmethod
    def _get_platform_keypair() -> Optional[Keypair]:
        """
        获取平台私钥对 - 支持多种来源

        Returns:
            Keypair: 平台私钥对，失败时返回None
        """
        try:
            # 尝试从多个来源获取加密的平台私钥
            encrypted_keypair = None
            source = 'unknown'

            # 1. 首先尝试从数据库系统配置获取
            try:
                from app.models.admin import SystemConfig
                db_keypair = SystemConfig.get_value('PLATFORM_SPL_KEYPAIR')
                if db_keypair:
                    encrypted_keypair = db_keypair
                    source = 'database'
                    logger.info("从数据库系统配置中获取平台私钥")
            except Exception as e:
                logger.warning(f"从数据库获取平台私钥失败: {e}")

            # 2. 如果数据库中没有，尝试从Flask配置中获取
            if not encrypted_keypair:
                config_keypair = current_app.config.get('PLATFORM_SPL_KEYPAIR')
                if config_keypair:
                    encrypted_keypair = config_keypair
                    source = 'flask_config'
                    logger.info("从Flask配置中获取平台私钥")

            if not encrypted_keypair:
                logger.error("配置中未找到PLATFORM_SPL_KEYPAIR")
                return None

            # 解密私钥
            keypair_hex = CryptoManager.decrypt_data(encrypted_keypair)
            keypair_bytes = bytes.fromhex(keypair_hex)

            keypair = Keypair.from_bytes(keypair_bytes)
            logger.info(f"平台私钥获取成功 (来源: {source}): {keypair.pubkey()}")
            return keypair

        except Exception as e:
            logger.error(f"获取平台私钥失败: {e}", exc_info=True)
            return None