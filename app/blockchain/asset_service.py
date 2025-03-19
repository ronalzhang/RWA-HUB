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
            private_key = os.environ.get('SOLANA_PRIVATE_KEY')
            if private_key:
                logger.info("使用配置的私钥初始化Solana客户端")
                self.solana_client = SolanaClient(private_key=private_key)
                return
                
            # 检查是否有助记词配置    
            mnemonic = os.environ.get('SOLANA_SERVICE_WALLET_MNEMONIC')
            if mnemonic:
                logger.info("使用配置的助记词初始化Solana客户端")
                self.solana_client = SolanaClient(mnemonic=mnemonic)
                return
                
            # 如果没有找到私钥或助记词，使用只读模式
            logger.warning("未找到钱包私钥或助记词，回退到只读模式")
            user_wallet = "EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR"
            logger.info(f"使用钱包地址（只读模式）: {user_wallet}")
            self.solana_client = SolanaClient(wallet_address=user_wallet)
        
    def deploy_asset_to_blockchain(self, asset_id):
        """
        将资产部署到区块链上
        
        Args:
            asset_id: 资产ID
            
        Returns:
            dict: 包含部署结果的字典
        """
        try:
            # 获取资产
            asset = Asset.query.get(asset_id)
            if not asset:
                raise ValueError(f"未找到ID为{asset_id}的资产")
                
            # 检查资产状态
            if asset.status != AssetStatus.APPROVED.value:
                raise ValueError(f"资产必须是已审核状态才能部署到区块链")
                
            # 如果已经有token_address，说明已经部署过
            if asset.token_address:
                logger.info(f"资产{asset_id}已经部署过，token_address: {asset.token_address}")
                return {
                    "success": True,
                    "message": "资产已经部署到区块链",
                    "token_address": asset.token_address,
                    "tx_hash": asset.deployment_tx_hash,
                    "already_deployed": True
                }
                
            # 模拟模式下，直接返回模拟数据
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
                
            # 检查钱包余额是否足够
            if not self.solana_client.check_balance_sufficient():
                raise ValueError("服务钱包SOL余额不足，无法创建代币")
                
            # 创建SPL代币
            token_result = self.solana_client.create_spl_token(
                asset_name=asset.name,
                token_symbol=asset.token_symbol,
                token_supply=asset.token_supply,
                decimals=9  # 默认使用9位小数
            )
            
            if token_result.get('success', False):
                # 更新资产状态
                token_address = token_result.get('token_address')
                
                asset.token_address = token_address
                asset.status = AssetStatus.APPROVED.value
                asset.approved_at = datetime.utcnow()
                asset.approved_by = asset.creator_address  # 自动审核
                
                # 存储上链详情
                asset.blockchain_details = json.dumps(token_result.get('details', {}))
                
                # 保存更新
                db.session.commit()
                
                logger.info(f"资产成功上链: {asset_id}, 代币地址: {token_address}")
                
                return {
                    'success': True,
                    'asset_id': asset_id,
                    'token_address': token_address,
                    'details': token_result.get('details', {})
                }
            else:
                logger.error(f"资产上链失败: {asset_id}, 错误: {token_result.get('error')}")
                return token_result
                
        except Exception as e:
            logger.exception(f"部署资产过程中发生异常: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': f"部署资产异常: {str(e)}"
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
            private_key = os.environ.get('SOLANA_PRIVATE_KEY')
            if private_key:
                solana_client = SolanaClient(private_key=private_key)
            else:
                # 检查是否有助记词配置
                mnemonic = os.environ.get('SOLANA_SERVICE_WALLET_MNEMONIC')
                if mnemonic:
                    solana_client = SolanaClient(mnemonic=mnemonic)
                else:
                    # 如果没有私钥或助记词，使用只读模式
                    solana_client = SolanaClient(wallet_address="EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR")
            
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