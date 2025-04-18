from flask import current_app
from datetime import datetime
import logging
import json
from .solana import SolanaClient
from app.models import Asset, AssetStatus
from app.extensions import db
import os
import traceback
import base58
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from decimal import Decimal
from flask import current_app, g
from app.models.user import User
from app.models.transaction import Transaction as DBTransaction, TransactionType, TransactionStatus
from app.models.holding import Holding
from app.utils.config import load_config
from app.utils.constants import MIN_SOL_BALANCE
from app.utils.transaction_helpers import record_fee_transaction
from app.utils.solana_compat.rpc.api import Client
from app.utils.solana_compat.publickey import PublicKey
from app.blockchain.ethereum import get_usdc_balance, get_eth_balance, send_usdc, deploy_asset_contract, create_purchase_transaction

logger = logging.getLogger(__name__)

class AssetService:
    """
    资产服务类，协调资产数据和区块链上链操作
    """
    
    def __init__(self, solana_client=None):
        """
        初始化资产服务
        
        Args:
            solana_client: 可选的Solana客户端实例
        """
        if solana_client:
            self.solana_client = solana_client
        else:
            # 检查是否有私钥配置
            private_key = os.environ.get('SOLANA_SERVICE_WALLET_PRIVATE_KEY')
            if not private_key:
                # 兼容旧版本使用的私钥环境变量
                private_key = os.environ.get('SOLANA_PRIVATE_KEY')
                if private_key:
                    logger.info("使用SOLANA_PRIVATE_KEY环境变量初始化Solana客户端（为向后兼容）")
            
            if private_key:
                logger.info("使用配置的私钥初始化Solana客户端")
                self.solana_client = SolanaClient(private_key=private_key)
                return
                
            # 检查是否有助记词配置（已废弃，仅保留向后兼容）    
            mnemonic = os.environ.get('SOLANA_SERVICE_WALLET_MNEMONIC')
            if mnemonic:
                logger.warning("使用助记词初始化Solana客户端，此方法已废弃，建议使用私钥")
                self.solana_client = SolanaClient(mnemonic=mnemonic)
                return
                
            # 如果没有找到私钥或助记词，使用只读模式
            logger.warning("未找到钱包私钥或助记词，回退到只读模式")
            user_wallet = "HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd"
            logger.info(f"使用钱包地址（只读模式）: {user_wallet}")
            self.solana_client = SolanaClient(wallet_address=user_wallet)
        
    def deploy_asset_to_blockchain(self, asset_id):
        """
        将资产部署到区块链上，并在成功或失败时更新数据库状态
        
        Args:
            asset_id: 资产ID
            
        Returns:
            dict: 包含部署结果的字典
        """
        asset = None # 初始化 asset 变量
        try:
            # 获取资产
            asset = Asset.query.get(asset_id)
            if not asset:
                raise ValueError(f"未找到ID为{asset_id}的资产")
                
            # 检查资产状态 - 应该是在 CONFIRMED 状态才能上链
            if asset.status != AssetStatus.CONFIRMED.value:
                logger.warning(f"尝试部署状态不正确的资产: AssetID={asset_id}, Status={asset.status}. 预期状态: CONFIRMED")
                # 可以选择直接返回失败，或尝试继续（取决于业务逻辑）
                # 这里选择返回失败，因为支付确认是前置条件
                return {
                    "success": False,
                    "error": f"资产状态不正确 ({asset.status})，无法部署。预期状态: CONFIRMED"
                }
                
            # 如果已经有token_address，说明已经部署过 (再次检查，以防万一)
            if asset.token_address:
                logger.info(f"资产{asset_id}已经部署过，token_address: {asset.token_address}")
                # 确保状态是 ON_CHAIN
                if asset.status != AssetStatus.ON_CHAIN.value:
                     asset.status = AssetStatus.ON_CHAIN.value
                     db.session.commit()
                return {
                    "success": True,
                    "message": "资产已经部署到区块链",
                    "token_address": asset.token_address,
                    "already_deployed": True
                }
                
            # --- 开始实际部署 --- 
            logger.info(f"开始将资产部署到区块链: AssetID={asset_id}, Name={asset.name}")
            
            # 可以在这里临时更新状态为 DEPLOYING (如果需要更细粒度的状态)
            # asset.status = AssetStatus.DEPLOYING.value
            # db.session.commit()
            
            # 模拟模式处理 (保持不变)
            if getattr(self.solana_client, 'mock_mode', False):
                logger.info(f"模拟模式：部署资产 {asset.name} 到区块链")
                
                # 生成模拟的token地址和交易hash
                seed = f"{asset.name}_{asset.token_symbol}_{int(time.time())}".encode()
                hash_bytes = hashlib.sha256(seed).digest()[:32]
                token_address = "So" + base58.b58encode(hash_bytes).decode()[:40]
                tx_hash = base58.b58encode(hashlib.sha256(f"{token_address}_{int(time.time())}".encode()).digest()).decode()
                
                # 更新资产信息
                asset.token_address = token_address
                asset.deployment_tx_hash = tx_hash
                asset.status = AssetStatus.ON_CHAIN.value
                asset.deployment_time = datetime.utcnow()
                
                # 构建blockchain_details
                blockchain_details = {
                    "network": "solana_mainnet",
                    "token_type": "spl",
                    "decimals": 9,
                    "deployment_time": datetime.now().isoformat(),
                    "creator": str(self.solana_client.public_key),
                    "supply": asset.token_supply,
                    "mock_mode": True
                }
                
                # 如果数据库有blockchain_details字段，则设置
                if hasattr(asset, 'blockchain_details'):
                    asset.blockchain_details = json.dumps(blockchain_details)
                
                # 保存到数据库
                db.session.commit()
                
                logger.info(f"模拟模式：成功部署资产 {asset.name} 到区块链，token地址: {token_address}")
                return {
                    "success": True,
                    "message": "资产成功部署到区块链（模拟模式）",
                    "token_address": token_address,
                    "tx_hash": tx_hash,
                    "mock": True
                }
            
            # 检查服务钱包余额 (保持不变)
            if not self.solana_client.check_balance_sufficient():
                raise ValueError("服务钱包SOL余额不足，无法创建代币")
                
            # --- 调用 Solana 客户端创建 SPL 代币 --- 
            token_result = self.solana_client.create_spl_token(
                asset_name=asset.name,
                token_symbol=asset.token_symbol,
                token_supply=asset.token_supply,
                decimals=9  # 或从资产配置读取
            )
            
            # --- 处理部署结果 --- 
            if token_result.get('success', False):
                # 部署成功
                token_address = token_result.get('token_address')
                tx_hash = token_result.get('tx_hash') # 获取交易哈希
                details = token_result.get('details', {})
                
                asset.token_address = token_address
                asset.deployment_tx_hash = tx_hash
                asset.status = AssetStatus.ON_CHAIN.value # 更新状态为 ON_CHAIN
                asset.deployment_time = datetime.utcnow()
                asset.blockchain_details = json.dumps(details)
                
                db.session.commit()
                logger.info(f"资产成功上链: AssetID={asset_id}, TokenAddress={token_address}, Status=ON_CHAIN")
                
                return {
                    'success': True,
                    'asset_id': asset_id,
                    'token_address': token_address,
                    'tx_hash': tx_hash,
                    'details': details
                }
            else:
                # 部署失败
                error_message = token_result.get('error', '部署到区块链失败')
                logger.error(f"资产上链失败: AssetID={asset_id}, Error: {error_message}")
                
                # 更新资产状态为部署失败
                asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                asset.error_message = error_message
                db.session.commit()
                
                return {
                    'success': False,
                    'error': error_message
                }
                
        except Exception as e:
            error_str = f"部署资产异常: {str(e)}"
            logger.exception(error_str) # 使用 exception 记录完整堆栈
            if asset: # 只有在成功获取 asset 对象后才尝试更新状态
                 try:
                     # 发生未知异常时，也标记为部署失败
                     asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                     asset.error_message = error_str
                     db.session.commit()
                     logger.info(f"资产状态因异常更新为 DEPLOYMENT_FAILED: AssetID={asset_id}")
                 except Exception as db_err:
                     logger.error(f"在异常处理中更新资产状态失败: AssetID={asset_id}, DB Error: {str(db_err)}")
                     db.session.rollback()
            else:
                 logger.error(f"无法更新资产状态，因为未能获取资产对象: AssetID={asset_id}")
                 
            return {
                'success': False,
                'error': error_str
            }
            
    def process_asset_payment(self, asset_id, payment_info):
        """
        处理资产支付并触发上链
        
        Args:
            asset_id: 资产ID
            payment_info: 支付信息
            
        Returns:
            dict: 处理结果
        """
        try:
            # 获取资产
            asset = Asset.query.get(asset_id)
            if not asset:
                logger.error(f"资产不存在: {asset_id}")
                return {
                    'success': False,
                    'error': f"资产不存在: {asset_id}"
                }
                
            logger.info(f"处理资产支付: {asset_id}, 支付信息: {payment_info}")
            
            # 检查支付金额
            min_payment = float(os.environ.get('MIN_PAYMENT_AMOUNT', 100))
            payment_amount = float(payment_info.get('amount', 0))
            
            if payment_amount < min_payment:
                logger.warning(f"支付金额不足: {payment_amount} USDC, 最低要求: {min_payment} USDC")
                return {
                    'success': False,
                    'error': f"支付金额不足: {payment_amount} USDC, 最低要求: {min_payment} USDC"
                }
                
            # 验证支付状态
            payment_status = payment_info.get('status')
            if payment_status != 'confirmed':
                logger.warning(f"支付未确认: {payment_status}")
                return {
                    'success': False,
                    'error': f"支付未确认: {payment_status}"
                }
                
            # 记录支付信息
            if not hasattr(asset, 'payment_details') or not asset.payment_details:
                asset.payment_details = json.dumps(payment_info)
                asset.payment_confirmed = True
                asset.payment_confirmed_at = datetime.utcnow()
                db.session.commit()
                
            # 触发上链流程
            deploy_result = self.deploy_asset_to_blockchain(asset_id)
            
            return {
                'success': deploy_result.get('success', False),
                'payment_processed': True,
                'deploy_result': deploy_result
            }
            
        except Exception as e:
            logger.exception(f"处理资产支付过程中发生异常: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': f"处理支付异常: {str(e)}"
            }
    
    @staticmethod
    def get_service_wallet_status():
        """
        获取服务钱包状态
        
        Returns:
            dict: 服务钱包状态信息
        """
        try:
            logger.info("开始检查服务钱包状态")
            
            # 检查是否有私钥配置
            private_key = os.environ.get('SOLANA_SERVICE_WALLET_PRIVATE_KEY')
            if not private_key:
                # 兼容旧版本使用的私钥环境变量
                private_key = os.environ.get('SOLANA_PRIVATE_KEY')
                if private_key:
                    logger.info("使用SOLANA_PRIVATE_KEY环境变量获取钱包状态（为向后兼容）")
            
            if private_key:
                solana_client = SolanaClient(private_key=private_key)
            else:
                # 检查是否有助记词配置（已废弃，仅向后兼容）
                mnemonic = os.environ.get('SOLANA_SERVICE_WALLET_MNEMONIC')
                if mnemonic:
                    logger.warning("使用助记词获取钱包状态，此方法已废弃，建议使用私钥")
                    solana_client = SolanaClient(mnemonic=mnemonic)
                else:
                    # 如果没有私钥或助记词，使用只读模式
                    solana_client = SolanaClient(wallet_address="HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd")
            
            # 检查客户端是否成功初始化了公钥
            if not solana_client.public_key:
                logger.warning("Solana客户端未初始化公钥，返回降级状态")
                return {
                    'success': False,
                    'error': '未初始化钱包公钥，无法查询余额',
                    'wallet_initialized': False,
                    'needs_setup': True,
                    'network': solana_client.network_url,
                    'env_vars_found': [k for k in os.environ.keys() if k.startswith('SOLANA_')]
                }
            
            # 尝试获取余额
            try:
                balance = solana_client.get_balance()
                logger.info(f"查询余额结果: {balance}")
            except ValueError as e:
                logger.error(f"获取余额失败: {str(e)}")
                # 返回降级状态但至少有钱包地址
                return {
                    'success': False,
                    'error': str(e),
                    'wallet_initialized': True,
                    'wallet_address': str(solana_client.public_key),
                    'balance_error': True
                }
            
            threshold = float(os.environ.get('SOLANA_BALANCE_THRESHOLD', 0.1))
            is_sufficient = balance is not None and balance >= threshold
            
            # 检查是否处于只读模式
            readonly = getattr(solana_client, 'readonly_mode', False)
            
            return {
                'success': True,
                'balance': balance,
                'balance_sol': balance,
                'threshold': threshold,
                'is_sufficient': is_sufficient,
                'wallet_address': str(solana_client.public_key),
                'network': solana_client.network_url,
                'readonly_mode': readonly,
                'transaction_capable': not readonly and balance is not None and balance > 0
            }
        except Exception as e:
            logger.exception(f"获取服务钱包状态异常: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'detail': traceback.format_exc()
            }
            
    @staticmethod
    def get_token_balance(wallet_address, token_mint_address):
        """
        获取特定SPL代币在钱包中的余额
        
        Args:
            wallet_address: 钱包地址
            token_mint_address: 代币铸造地址
            
        Returns:
            float: 代币余额
        """
        try:
            logger.info(f"开始获取钱包 {wallet_address} 的代币 {token_mint_address} 余额")
            
            # 验证输入参数
            if not wallet_address or not token_mint_address:
                logger.error("钱包地址或代币地址为空")
                return 0.0
            
            # 检查USDC代币地址是否正确（Solana主网）
            expected_usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            if token_mint_address != expected_usdc_address:
                logger.warning(f"请求的代币地址 {token_mint_address} 不是标准USDC地址 {expected_usdc_address}")
            
            # 初始化Solana客户端
            try:
                from app.blockchain.solana import SolanaClient
                solana_client = SolanaClient(wallet_address=wallet_address)
                network_url = solana_client.network_url
                logger.info(f"Solana客户端初始化成功，网络URL: {network_url}")
            except Exception as client_err:
                logger.error(f"Solana客户端初始化失败: {str(client_err)}")
                return 0.0
            
            # 检查是否处于模拟模式
            if getattr(solana_client, 'mock_mode', False):
                logger.info("模拟模式：返回模拟的代币余额")
                return 0.0
            
            # 导入所需模块
            try:
                from solders.pubkey import Pubkey as PublicKey
                import spl.token.client
                logger.info("成功导入Solana相关模块")
            except ImportError as import_err:
                logger.error(f"导入Solana模块失败: {str(import_err)}")
                try:
                    # 尝试备用导入
                    from solana.publickey import PublicKey
                    import spl.token.client
                    logger.info("使用备用方式成功导入Solana模块")
                except ImportError:
                    logger.error("备用导入也失败，无法获取余额")
                    return 0.0
            
            # 创建RPC客户端
            try:
                try:
                    from solana.rpc.api import Client
                except ImportError:
                    from app.utils.solana_compat.rpc.api import Client
                
                rpc_client = Client(solana_client.network_url)
                logger.info(f"创建RPC客户端成功，连接到: {solana_client.network_url}")
            except Exception as rpc_err:
                logger.error(f"创建RPC客户端失败: {str(rpc_err)}")
                return 0.0
            
            # 获取代币账户信息
            try:
                # 验证公钥格式
                try:
                    wallet_pubkey = PublicKey(wallet_address)
                    token_mint_pubkey = PublicKey(token_mint_address)
                    logger.info(f"成功创建公钥对象: 钱包={wallet_pubkey}, 代币={token_mint_pubkey}")
                except Exception as pubkey_err:
                    logger.error(f"创建公钥对象失败: {str(pubkey_err)}")
                    return 0.0
                
                # 使用spl.token库获取代币账户信息
                try:
                    token = spl.token.client.Token(
                        conn=rpc_client,
                        pubkey=token_mint_pubkey,
                        program_id=spl.token.constants.TOKEN_PROGRAM_ID,
                        payer=None
                    )
                    logger.info(f"成功创建Token对象: {token_mint_address}")
                except Exception as token_err:
                    logger.error(f"创建Token对象失败: {str(token_err)}")
                    return 0.0
                
                # 获取钱包的代币账户
                logger.info(f"开始获取钱包的代币账户: {wallet_address}")
                try:
                    token_accounts_response = rpc_client.get_token_accounts_by_owner(
                        wallet_pubkey,
                        {'mint': token_mint_pubkey}
                    )
                    logger.info(f"代币账户响应: {json.dumps(token_accounts_response, default=str)[:200]}...")
                except Exception as accounts_err:
                    logger.error(f"获取代币账户失败: {str(accounts_err)}")
                    return 0.0
                
                token_accounts = token_accounts_response.get('result', {}).get('value', [])
                logger.info(f"找到 {len(token_accounts)} 个代币账户")
                
                balance = 0.0
                decimals = 6  # USDC默认为6位小数
                
                # 如果找到代币账户，获取余额
                if token_accounts:
                    for account in token_accounts:
                        account_pubkey = account.get('pubkey')
                        logger.info(f"处理代币账户: {account_pubkey}")
                        
                        try:
                            balance_response = rpc_client.get_token_account_balance(account_pubkey)
                            logger.info(f"余额响应: {json.dumps(balance_response, default=str)}")
                        except Exception as balance_err:
                            logger.error(f"获取账户余额失败: {str(balance_err)}")
                            continue
                        
                        account_data = balance_response.get('result', {}).get('value', {})
                        if account_data:
                            amount = float(account_data.get('amount', '0'))
                            if 'decimals' in account_data:
                                decimals = int(account_data.get('decimals'))
                            current_balance = amount / (10 ** decimals)
                            logger.info(f"账户 {account_pubkey} 余额: {current_balance} (原始: {amount}, 小数位: {decimals})")
                            balance += current_balance
                else:
                    logger.warning(f"未找到钱包 {wallet_address} 的 {token_mint_address} 代币账户")
                
                logger.info(f"成功获取代币余额: {balance} (decimals={decimals})")
                return balance
            except Exception as e:
                logger.error(f"获取代币账户和余额失败: {str(e)}")
                logger.error(traceback.format_exc())
                return 0.0
        except Exception as e:
            logger.error(f"获取代币余额过程中发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return 0.0 