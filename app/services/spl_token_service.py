import logging
import time
import json
import base64
from typing import Dict, Optional, Tuple
from decimal import Decimal
from flask import current_app
import requests
import hashlib

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import create_account, CreateAccountParams
from solders.instruction import Instruction
from spl.token.instructions import (
    initialize_mint, mint_to, create_associated_token_account,
    get_associated_token_address, InitializeMintParams, MintToParams,
    transfer, TransferParams, burn, BurnParams
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

            # 2. 创建元数据
            metadata_result = SplTokenService._create_token_metadata(asset, operation_id)
            if not metadata_result['success']:
                return metadata_result

            metadata_uri = metadata_result['data']['metadata_uri']
            logger.info(f"[{operation_id}] 元数据创建成功: {metadata_uri}")

            # 3. 生成Token mint keypair
            mint_keypair = Keypair()
            mint_pubkey = mint_keypair.pubkey()
            mint_address = str(mint_pubkey)

            logger.info(f"[{operation_id}] 生成Mint地址: {mint_address}")

            # 4. 生成mint权限keypair（平台控制）
            mint_authority_keypair = Keypair()
            mint_authority_pubkey = mint_authority_keypair.pubkey()

            # 5. 获取平台支付keypair
            if not platform_keypair:
                platform_keypair = SplTokenService._get_platform_keypair()
                if not platform_keypair:
                    return {
                        'success': False,
                        'error': 'PLATFORM_KEYPAIR_ERROR',
                        'message': '无法获取平台私钥，请检查配置'
                    }

            platform_pubkey = platform_keypair.pubkey()

            # 6. 获取Solana客户端和最新区块哈希
            client = get_solana_client()
            recent_blockhash = get_latest_blockhash_with_cache()

            # 7. 计算所需的账户租金
            mint_account_space = 82  # SPL Token Mint账户大小
            mint_rent = client.get_minimum_balance_for_rent_exemption(mint_account_space).value

            logger.info(f"[{operation_id}] Mint账户租金: {mint_rent} lamports")

            # 8. 创建交易指令
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

            # 9. 构建并签名交易
            message = Message.new_with_blockhash(
                instructions,
                platform_pubkey,
                recent_blockhash
            )
            transaction = Transaction.new_unsigned(message)

            # 签名交易（需要平台密钥和mint密钥）
            transaction.sign([platform_keypair, mint_keypair], recent_blockhash)

            logger.info(f"[{operation_id}] 交易已签名，准备发送")

            # 10. 发送交易
            tx_response = client.send_raw_transaction(bytes(transaction))
            tx_hash = str(tx_response.value)

            logger.info(f"[{operation_id}] 交易已发送: {tx_hash}")

            # 11. 等待确认
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

            # 12. 更新数据库
            try:
                # 加密存储mint权限私钥
                crypto_manager = CryptoManager()
                encrypted_mint_authority = crypto_manager.encrypt_private_key(
                    bytes(mint_authority_keypair).hex()
                )

                # 更新资产记录
                asset.spl_mint_address = mint_address
                asset.mint_authority_keypair = encrypted_mint_authority
                asset.metadata_uri = metadata_uri
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

            # 13. 返回成功结果
            return {
                'success': True,
                'message': f'SPL Token创建成功: {asset.token_symbol}',
                'data': {
                    'mint_address': mint_address,
                    'mint_authority': str(mint_authority_pubkey),
                    'metadata_uri': metadata_uri,
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
                crypto_manager = CryptoManager()
                mint_authority_hex = crypto_manager.decrypt_private_key(encrypted_mint_authority)
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
            crypto_manager = CryptoManager()
            keypair_hex = crypto_manager.decrypt_private_key(encrypted_keypair)
            keypair_bytes = bytes.fromhex(keypair_hex)

            keypair = Keypair.from_bytes(keypair_bytes)
            logger.info(f"平台私钥获取成功 (来源: {source}): {keypair.pubkey()}")
            return keypair

        except Exception as e:
            logger.error(f"获取平台私钥失败: {e}", exc_info=True)
            return None

    @staticmethod
    def _create_token_metadata(asset, operation_id: str) -> Dict:
        """
        创建Token元数据

        Args:
            asset: 资产对象
            operation_id: 操作ID

        Returns:
            dict: 元数据创建结果
        """
        try:
            logger.info(f"[{operation_id}] 开始创建Token元数据")

            # 1. 构建元数据内容
            metadata = {
                "name": f"{asset.name} Token",
                "symbol": asset.token_symbol,
                "description": asset.description or f"Tokenized asset: {asset.name}",
                "image": SplTokenService._get_asset_image_url(asset),
                "attributes": [
                    {
                        "trait_type": "Asset Type",
                        "value": SplTokenService._get_asset_type_name(asset.asset_type)
                    },
                    {
                        "trait_type": "Location",
                        "value": asset.location
                    },
                    {
                        "trait_type": "Total Supply",
                        "value": str(asset.token_supply)
                    },
                    {
                        "trait_type": "Token Price",
                        "value": f"{asset.token_price} USDC"
                    },
                    {
                        "trait_type": "Annual Revenue",
                        "value": f"{asset.annual_revenue} USDC"
                    }
                ],
                "properties": {
                    "files": [
                        {
                            "uri": SplTokenService._get_asset_image_url(asset),
                            "type": "image/png"
                        }
                    ],
                    "category": "image",
                    "creators": [
                        {
                            "address": asset.creator_address,
                            "share": 100
                        }
                    ]
                }
            }

            # 添加面积信息（如果存在）
            if asset.area:
                metadata["attributes"].append({
                    "trait_type": "Area",
                    "value": f"{asset.area} sqm"
                })

            # 添加总价值信息（如果存在）
            if asset.total_value:
                metadata["attributes"].append({
                    "trait_type": "Total Value",
                    "value": f"{asset.total_value} USDC"
                })

            logger.info(f"[{operation_id}] 元数据内容构建完成")

            # 2. 上传元数据到IPFS或其他存储
            metadata_uri = SplTokenService._upload_metadata(metadata, operation_id)
            if not metadata_uri:
                return {
                    'success': False,
                    'error': 'METADATA_UPLOAD_FAILED',
                    'message': '元数据上传失败'
                }

            return {
                'success': True,
                'data': {
                    'metadata': metadata,
                    'metadata_uri': metadata_uri
                }
            }

        except Exception as e:
            logger.error(f"[{operation_id}] 创建Token元数据失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'METADATA_CREATION_ERROR',
                'message': f'创建Token元数据失败: {str(e)}'
            }

    @staticmethod
    def _get_asset_image_url(asset) -> str:
        """获取资产图片URL"""
        try:
            images = asset.images
            if images and len(images) > 0:
                # 返回第一张图片
                return images[0]
            else:
                # 使用默认图片
                return f"{current_app.config.get('BASE_URL', 'https://rwa-hub.com')}/static/images/default-asset.png"
        except Exception as e:
            logger.warning(f"获取资产图片失败: {e}")
            return f"{current_app.config.get('BASE_URL', 'https://rwa-hub.com')}/static/images/default-asset.png"

    @staticmethod
    def _get_asset_type_name(asset_type: int) -> str:
        """获取资产类型名称"""
        from app.models.asset import AssetType
        try:
            for atype in AssetType:
                if atype.value == asset_type:
                    return atype.name.replace('_', ' ').title()
            return "Unknown"
        except Exception:
            return "Unknown"

    @staticmethod
    def _upload_metadata(metadata: dict, operation_id: str) -> Optional[str]:
        """
        上传元数据到去中心化存储

        Args:
            metadata: 元数据内容
            operation_id: 操作ID

        Returns:
            str: 元数据URI，失败时返回None
        """
        try:
            # 方法1: 尝试使用NFT.Storage (免费IPFS服务)
            nft_storage_result = SplTokenService._upload_to_nft_storage(metadata, operation_id)
            if nft_storage_result:
                return nft_storage_result

            # 方法2: 回退到本地存储模拟IPFS
            local_result = SplTokenService._store_metadata_locally(metadata, operation_id)
            if local_result:
                return local_result

            logger.error(f"[{operation_id}] 所有元数据上传方法都失败")
            return None

        except Exception as e:
            logger.error(f"[{operation_id}] 上传元数据失败: {e}", exc_info=True)
            return None

    @staticmethod
    def _upload_to_nft_storage(metadata: dict, operation_id: str) -> Optional[str]:
        """上传到NFT.Storage (免费IPFS)"""
        try:
            # 获取API密钥
            api_key = current_app.config.get('NFT_STORAGE_API_KEY')
            if not api_key:
                logger.warning(f"[{operation_id}] NFT.Storage API密钥未配置")
                return None

            # 上传到NFT.Storage
            url = "https://api.nft.storage/upload"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.post(url, json=metadata, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                ipfs_hash = result.get('value', {}).get('cid')
                if ipfs_hash:
                    metadata_uri = f"https://ipfs.io/ipfs/{ipfs_hash}"
                    logger.info(f"[{operation_id}] 元数据上传到NFT.Storage成功: {metadata_uri}")
                    return metadata_uri

            logger.warning(f"[{operation_id}] NFT.Storage上传失败: {response.status_code}")
            return None

        except Exception as e:
            logger.warning(f"[{operation_id}] NFT.Storage上传异常: {e}")
            return None

    @staticmethod
    def _store_metadata_locally(metadata: dict, operation_id: str) -> Optional[str]:
        """本地存储元数据并提供公共URL"""
        try:
            import os
            from flask import url_for

            # 创建元数据存储目录
            metadata_dir = os.path.join(current_app.root_path, 'static', 'metadata')
            os.makedirs(metadata_dir, exist_ok=True)

            # 生成文件名（使用内容哈希确保唯一性）
            metadata_str = json.dumps(metadata, sort_keys=True)
            metadata_hash = hashlib.md5(metadata_str.encode()).hexdigest()
            filename = f"{metadata_hash}.json"

            file_path = os.path.join(metadata_dir, filename)

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # 生成公共URL
            base_url = current_app.config.get('BASE_URL', 'https://rwa-hub.com')
            metadata_uri = f"{base_url}/static/metadata/{filename}"

            logger.info(f"[{operation_id}] 元数据本地存储成功: {metadata_uri}")
            return metadata_uri

        except Exception as e:
            logger.error(f"[{operation_id}] 本地存储元数据失败: {e}")
            return None

    @staticmethod
    def get_token_metadata(mint_address: str) -> Dict:
        """
        获取Token元数据

        Args:
            mint_address: Token mint地址

        Returns:
            dict: 元数据信息
        """
        try:
            # 从数据库查找对应的资产
            asset = Asset.query.filter_by(spl_mint_address=mint_address).first()
            if not asset or not asset.metadata_uri:
                return {
                    'success': False,
                    'error': 'METADATA_NOT_FOUND',
                    'message': f'未找到mint地址 {mint_address} 对应的元数据'
                }

            # 获取元数据内容
            try:
                response = requests.get(asset.metadata_uri, timeout=10)
                if response.status_code == 200:
                    metadata = response.json()
                    return {
                        'success': True,
                        'data': {
                            'metadata_uri': asset.metadata_uri,
                            'metadata': metadata
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': 'METADATA_FETCH_FAILED',
                        'message': f'获取元数据失败，状态码: {response.status_code}'
                    }
            except Exception as fetch_error:
                return {
                    'success': False,
                    'error': 'METADATA_FETCH_ERROR',
                    'message': f'获取元数据异常: {str(fetch_error)}'
                }

        except Exception as e:
            logger.error(f"获取Token元数据失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'METADATA_QUERY_ERROR',
                'message': f'查询Token元数据失败: {str(e)}'
            }

    @staticmethod
    def transfer_tokens(
        mint_address: str,
        from_address: str,
        to_address: str,
        amount: int,
        from_private_key: str = None
    ) -> Dict:
        """
        转移Token给其他用户

        Args:
            mint_address: Token mint地址
            from_address: 发送者钱包地址
            to_address: 接收者钱包地址
            amount: 转移数量
            from_private_key: 发送者私钥（可选，用于平台代理转账）

        Returns:
            dict: 转移结果
        """
        operation_id = f"transfer_{mint_address[:8]}_{from_address[:8]}_{to_address[:8]}_{int(time.time())}"
        logger.info(f"[{operation_id}] 开始转移 {amount} 个代币从 {from_address} 到 {to_address}")

        try:
            # 1. 验证参数
            if amount <= 0:
                return {
                    'success': False,
                    'error': 'INVALID_AMOUNT',
                    'message': '转移数量必须大于0'
                }

            # 2. 获取必要的公钥
            mint_pubkey = Pubkey.from_string(mint_address)
            from_pubkey = Pubkey.from_string(from_address)
            to_pubkey = Pubkey.from_string(to_address)

            # 3. 获取关联代币账户地址
            from_token_account = get_associated_token_address(from_pubkey, mint_pubkey)
            to_token_account = get_associated_token_address(to_pubkey, mint_pubkey)

            # 4. 获取Solana客户端
            client = get_solana_client()

            # 5. 检查发送者代币账户余额
            from_account_info = client.get_token_account_balance(from_token_account)
            if not from_account_info.value or int(from_account_info.value.amount) < amount:
                return {
                    'success': False,
                    'error': 'INSUFFICIENT_BALANCE',
                    'message': f'发送者余额不足，当前余额: {from_account_info.value.amount if from_account_info.value else 0}'
                }

            # 6. 检查接收者代币账户是否存在
            to_account_info = client.get_account_info(to_token_account)

            instructions = []

            # 7. 如果接收者代币账户不存在，创建它
            if not to_account_info.value:
                logger.info(f"[{operation_id}] 创建接收者代币账户: {to_token_account}")

                # 获取平台keypair支付账户创建费用
                platform_keypair = SplTokenService._get_platform_keypair()
                if not platform_keypair:
                    return {
                        'success': False,
                        'error': 'PLATFORM_KEYPAIR_ERROR',
                        'message': '无法获取平台私钥用于支付账户创建费用'
                    }

                create_ata_instruction = create_associated_token_account(
                    payer=platform_keypair.pubkey(),
                    owner=to_pubkey,
                    mint=mint_pubkey
                )
                instructions.append(create_ata_instruction)

            # 8. 创建转账指令
            transfer_instruction = transfer(
                TransferParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=from_token_account,
                    dest=to_token_account,
                    owner=from_pubkey,
                    amount=amount
                )
            )
            instructions.append(transfer_instruction)

            logger.info(f"[{operation_id}] 创建了 {len(instructions)} 个指令")

            # 9. 构建交易
            recent_blockhash = get_latest_blockhash_with_cache()

            # 确定交易支付者
            if from_private_key:
                # 使用提供的私钥进行转账
                from_keypair = Keypair.from_bytes(bytes.fromhex(from_private_key))
                payer_keypair = from_keypair
            else:
                # 使用平台私钥支付（需要发送者预先签名）
                platform_keypair = SplTokenService._get_platform_keypair()
                if not platform_keypair:
                    return {
                        'success': False,
                        'error': 'PLATFORM_KEYPAIR_ERROR',
                        'message': '无法获取平台私钥'
                    }
                payer_keypair = platform_keypair

            message = Message.new_with_blockhash(
                instructions,
                payer_keypair.pubkey(),
                recent_blockhash
            )
            transaction = Transaction.new_unsigned(message)

            # 10. 签名交易
            signers = [payer_keypair]
            if to_account_info.value is None and payer_keypair != platform_keypair:
                # 如果需要创建账户且不是平台支付，需要平台签名
                platform_keypair = SplTokenService._get_platform_keypair()
                signers.append(platform_keypair)

            transaction.sign(signers, recent_blockhash)

            # 11. 发送交易
            tx_response = client.send_raw_transaction(bytes(transaction))
            tx_hash = str(tx_response.value)

            logger.info(f"[{operation_id}] 转账交易已发送: {tx_hash}")

            # 12. 等待确认
            confirmation = client.confirm_transaction(tx_hash)
            if confirmation.value.err:
                logger.error(f"[{operation_id}] 转账交易确认失败: {confirmation.value.err}")
                return {
                    'success': False,
                    'error': 'TRANSACTION_FAILED',
                    'message': f'转账交易失败: {confirmation.value.err}',
                    'tx_hash': tx_hash
                }

            logger.info(f"[{operation_id}] 转账交易确认成功")

            return {
                'success': True,
                'message': f'成功转移 {amount} 个代币',
                'data': {
                    'mint_address': mint_address,
                    'from_address': from_address,
                    'to_address': to_address,
                    'from_token_account': str(from_token_account),
                    'to_token_account': str(to_token_account),
                    'amount': amount,
                    'tx_hash': tx_hash
                }
            }

        except Exception as e:
            logger.error(f"[{operation_id}] 转移代币失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'TRANSFER_ERROR',
                'message': f'转移代币失败: {str(e)}'
            }

    @staticmethod
    def burn_tokens(
        mint_address: str,
        owner_address: str,
        amount: int,
        owner_private_key: str = None
    ) -> Dict:
        """
        销毁Token

        Args:
            mint_address: Token mint地址
            owner_address: Token拥有者钱包地址
            amount: 销毁数量
            owner_private_key: 拥有者私钥（可选）

        Returns:
            dict: 销毁结果
        """
        operation_id = f"burn_{mint_address[:8]}_{owner_address[:8]}_{amount}_{int(time.time())}"
        logger.info(f"[{operation_id}] 开始销毁 {amount} 个代币，拥有者: {owner_address}")

        try:
            # 1. 验证参数
            if amount <= 0:
                return {
                    'success': False,
                    'error': 'INVALID_AMOUNT',
                    'message': '销毁数量必须大于0'
                }

            # 2. 获取必要的公钥
            mint_pubkey = Pubkey.from_string(mint_address)
            owner_pubkey = Pubkey.from_string(owner_address)

            # 3. 获取拥有者的关联代币账户地址
            owner_token_account = get_associated_token_address(owner_pubkey, mint_pubkey)

            # 4. 获取Solana客户端
            client = get_solana_client()

            # 5. 检查拥有者代币账户余额
            account_info = client.get_token_account_balance(owner_token_account)
            if not account_info.value:
                return {
                    'success': False,
                    'error': 'ACCOUNT_NOT_FOUND',
                    'message': '未找到代币账户'
                }

            current_balance = int(account_info.value.amount)
            if current_balance < amount:
                return {
                    'success': False,
                    'error': 'INSUFFICIENT_BALANCE',
                    'message': f'余额不足，当前余额: {current_balance}'
                }

            # 6. 获取私钥
            if owner_private_key:
                owner_keypair = Keypair.from_bytes(bytes.fromhex(owner_private_key))
            else:
                # 如果没有提供私钥，检查是否为平台管理的代币
                platform_keypair = SplTokenService._get_platform_keypair()
                if not platform_keypair:
                    return {
                        'success': False,
                        'error': 'PRIVATE_KEY_REQUIRED',
                        'message': '需要提供拥有者私钥进行销毁操作'
                    }
                owner_keypair = platform_keypair

            # 7. 创建销毁指令
            burn_instruction = burn(
                BurnParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=owner_token_account,
                    mint=mint_pubkey,
                    owner=owner_pubkey,
                    amount=amount
                )
            )

            instructions = [burn_instruction]

            logger.info(f"[{operation_id}] 创建了 {len(instructions)} 个指令")

            # 8. 构建并签名交易
            recent_blockhash = get_latest_blockhash_with_cache()
            message = Message.new_with_blockhash(
                instructions,
                owner_keypair.pubkey(),
                recent_blockhash
            )
            transaction = Transaction.new_unsigned(message)

            # 签名交易
            transaction.sign([owner_keypair], recent_blockhash)

            logger.info(f"[{operation_id}] 交易已签名，准备发送")

            # 9. 发送交易
            tx_response = client.send_raw_transaction(bytes(transaction))
            tx_hash = str(tx_response.value)

            logger.info(f"[{operation_id}] 销毁交易已发送: {tx_hash}")

            # 10. 等待确认
            confirmation = client.confirm_transaction(tx_hash)
            if confirmation.value.err:
                logger.error(f"[{operation_id}] 销毁交易确认失败: {confirmation.value.err}")
                return {
                    'success': False,
                    'error': 'TRANSACTION_FAILED',
                    'message': f'销毁交易失败: {confirmation.value.err}',
                    'tx_hash': tx_hash
                }

            logger.info(f"[{operation_id}] 销毁交易确认成功")

            # 11. 获取更新后的余额
            updated_account_info = client.get_token_account_balance(owner_token_account)
            new_balance = int(updated_account_info.value.amount) if updated_account_info.value else 0

            return {
                'success': True,
                'message': f'成功销毁 {amount} 个代币',
                'data': {
                    'mint_address': mint_address,
                    'owner_address': owner_address,
                    'owner_token_account': str(owner_token_account),
                    'burned_amount': amount,
                    'previous_balance': current_balance,
                    'new_balance': new_balance,
                    'tx_hash': tx_hash
                }
            }

        except Exception as e:
            logger.error(f"[{operation_id}] 销毁代币失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'BURN_ERROR',
                'message': f'销毁代币失败: {str(e)}'
            }

    @staticmethod
    def _get_status_name(status_code: int) -> str:
        """获取状态名称"""
        status_map = {
            0: 'pending',
            1: 'creating',
            2: 'completed',
            3: 'failed'
        }
        return status_map.get(status_code, 'unknown')