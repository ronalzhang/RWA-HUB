from flask import current_app
from datetime import datetime
import logging
import json
import requests
# from .solana import SolanaClient # <-- 已废弃
from app.blockchain.solana_service import get_solana_client # <-- 使用新的标准服务
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
# from app.utils.solana_compat.rpc.api import Client # <-- 已废弃
# from app.utils.solana_compat.publickey import PublicKey # <-- 已废弃
from solders.pubkey import Pubkey # <-- 使用新的标准库
from app.blockchain.ethereum import get_usdc_balance, get_eth_balance, send_usdc, deploy_asset_contract, create_purchase_transaction
from app.utils.helpers import get_solana_keypair_from_env

logger = logging.getLogger(__name__)

def get_proxy_config():
    """
    获取代理配置
    
    Returns:
        dict: 代理配置字典，如果没有配置代理则返回None
    """
    # 检查环境变量中的代理配置
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    
    # 如果没有设置代理环境变量，检查是否有自定义的Solana代理配置
    if not http_proxy and not https_proxy:
        solana_proxy = os.environ.get('SOLANA_RPC_PROXY')
        if solana_proxy:
            http_proxy = https_proxy = solana_proxy
    
    if http_proxy or https_proxy:
        proxy_config = {}
        if http_proxy:
            proxy_config['http'] = http_proxy
        if https_proxy:
            proxy_config['https'] = https_proxy
        
        logger.info(f"使用代理配置: {proxy_config}")
        return proxy_config
    
    logger.info("未配置代理")
    return None

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
        logger.warning("AssetService正在使用临时修复，部分功能（如资产部署）可能不可用。")
        if solana_client:
            self.solana_client = solana_client
        else:
            try:
                self.solana_client = get_solana_client()
            except Exception as e:
                logger.error(f"无法初始化新的Solana客户端: {e}", exc_info=True)
                self.solana_client = None
        
    def deploy_asset_to_blockchain(self, asset_id):
        """
        将资产部署到区块链上，并在成功或失败时更新数据库状态
        
        Args:
            asset_id: 资产ID
            
        Returns:
            dict: 包含部署结果的字典
        """
        logger.warning("deploy_asset_to_blockchain 功能已临时禁用以修复启动错误。")
        return {
            'success': False,
            'error': '此功能正在重构中，暂时不可用。'
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
        logger.warning("process_asset_payment 功能已临时禁用以修复启动错误。")
        return {
            'success': False,
            'error': '此功能正在重构中，暂时不可用。'
        }
    
    @staticmethod
    def get_service_wallet_status():
        """
        获取服务钱包状态
        
        Returns:
            dict: 服务钱包状态信息
        """
        logger.warning("get_service_wallet_status 功能已临时禁用以修复启动错误。")
        return {
            'success': False,
            'error': '此功能正在重构中，暂时不可用。'
        }
            
    @staticmethod
    def get_token_balance(wallet_address, token_mint_address=None):
        """
        获取特定SPL代币在钱包中的余额
        
        Args:
            wallet_address: 钱包地址
            token_mint_address: 代币铸造地址
            
        Returns:
            float: 代币余额
        """
        logger.warning("get_token_balance 功能已临时禁用以修复启动错误。")
        return 0.0

    @staticmethod
    def get_user_assets(wallet_address, wallet_type='metamask'):
        """
        获取用户的资产列表
        
        Args:
            wallet_address: 钱包地址
            wallet_type: 钱包类型
            
        Returns:
            list: 用户的资产列表
        """
        try:
            logger.info(f"开始获取用户 {wallet_address} 的资产列表，钱包类型: {wallet_type}")
            
            # 验证输入参数
            if not wallet_address:
                logger.error("钱包地址为空")
                return []
            
            # 针对不同钱包类型进行地址格式化
            if wallet_type.lower() in ['phantom', 'solflare', 'solana']:
                # Solana钱包地址保持原样
                formatted_address = wallet_address
            else:
                # 以太坊钱包地址转小写
                formatted_address = wallet_address.lower() if wallet_address.startswith('0x') else wallet_address
            
            logger.info(f"格式化后的钱包地址: {formatted_address}")
            
            # 从数据库查询用户的资产
            from app.models import Asset, Trade
            from app import db
            from sqlalchemy import or_, and_
            
            # 只查询用户购买的资产，不包括创建的资产
            logger.info("只查询用户购买的资产，不包括用户创建的资产")
            
            # 查询通过交易购买的资产
            purchased_assets = []
            try:
                from app.models import Trade
                # 获取用户所有的购买交易（包括completed和pending状态）
                from app.models.trade import TradeStatus, TradeType
                user_trades = Trade.query.filter(
                    Trade.trader_address == formatted_address,
                    Trade.type == TradeType.BUY.value,  # 使用字符串值 'buy'
                    Trade.status.in_([TradeStatus.COMPLETED.value, TradeStatus.PENDING.value])
                ).all()
                
                logger.info(f"找到用户 {formatted_address} 的交易记录: {len(user_trades)} 条")
                
                # 按资产ID分组，计算每个资产的总购买量
                asset_quantities = {}
                for trade in user_trades:
                    asset_id = trade.asset_id
                    amount = getattr(trade, 'amount', 0)
                    if asset_id in asset_quantities:
                        asset_quantities[asset_id] += amount
                    else:
                        asset_quantities[asset_id] = amount
                
                # 获取资产详情
                for asset_id, total_quantity in asset_quantities.items():
                    if total_quantity > 0:  # 只显示有数量的资产
                        try:
                            asset = Asset.query.get(asset_id)
                            if asset:
                                purchased_assets.append({
                                    'id': asset.id,
                                    'name': getattr(asset, 'name', 'Unknown Asset'),
                                    'token_symbol': getattr(asset, 'token_symbol', 'UNKNOWN'),
                                    'quantity': int(total_quantity),
                                    'symbol': getattr(asset, 'token_symbol', 'UNKNOWN')
                                })
                        except Exception as e:
                            logger.warning(f"处理购买资产 {asset_id} 失败: {str(e)}")
                            
                logger.info(f"从Trade表找到 {len(purchased_assets)} 个购买的资产")
                            
            except Exception as e:
                logger.warning(f"查询交易资产失败: {str(e)}")
            
            # 查询通过AssetOwnership表的资产（如果存在）
            try:
                from app.models import AssetOwnership
                asset_ownerships = AssetOwnership.query.filter_by(
                    owner_address=formatted_address,
                    status='active'
                ).all()
                
                for ownership in asset_ownerships:
                    try:
                        asset = Asset.query.get(ownership.asset_id)
                        if asset:
                            ownership_amount = getattr(ownership, 'amount', 0)
                            if ownership_amount > 0:
                                # 检查是否已在购买资产列表中
                                existing_asset = next((a for a in purchased_assets if a['id'] == asset.id), None)
                                if existing_asset:
                                    # 如果已存在，累加数量
                                    existing_asset['quantity'] += int(ownership_amount)
                                else:
                                    # 如果不存在，添加新资产
                                    purchased_assets.append({
                                        'id': asset.id,
                                        'name': getattr(asset, 'name', 'Unknown Asset'),
                                        'token_symbol': getattr(asset, 'token_symbol', 'UNKNOWN'),
                                        'quantity': int(ownership_amount),
                                        'symbol': getattr(asset, 'token_symbol', 'UNKNOWN')
                                    })
                    except Exception as e:
                        logger.warning(f"处理所有权资产失败: {str(e)}")
                        
                logger.info(f"从AssetOwnership表补充了资产信息")
            except ImportError:
                logger.info("AssetOwnership模型不存在，跳过所有权查询")
            except Exception as e:
                logger.warning(f"查询AssetOwnership失败: {str(e)}")
            
            # 尝试从Holdings表获取更准确的持仓数据
            try:
                from app.models.holding import Holding
                holdings = Holding.query.filter_by(
                    user_address=formatted_address,
                    status='active'
                ).all()
                
                for holding in holdings:
                    try:
                        asset = Asset.query.get(holding.asset_id)
                        if asset:
                            holding_amount = getattr(holding, 'amount', 0)
                            if holding_amount > 0:
                                # 检查是否已在购买资产列表中
                                existing_asset = next((a for a in purchased_assets if a['id'] == asset.id), None)
                                if existing_asset:
                                    # 如果已存在，使用Holdings表的数据（更准确）
                                    existing_asset['quantity'] = int(holding_amount)
                                else:
                                    # 如果不存在，添加新资产
                                    purchased_assets.append({
                                        'id': asset.id,
                                        'name': getattr(asset, 'name', 'Unknown Asset'),
                                        'token_symbol': getattr(asset, 'token_symbol', 'UNKNOWN'),
                                        'quantity': int(holding_amount),
                                        'symbol': getattr(asset, 'token_symbol', 'UNKNOWN')
                                    })
                    except Exception as e:
                        logger.warning(f"处理持仓资产失败: {str(e)}")
                        
                logger.info(f"从Holdings表找到 {len(holdings)} 个持仓记录")
            except ImportError:
                logger.info("Holdings模型不存在，跳过持仓查询")
            except Exception as e:
                logger.warning(f"查询Holdings失败: {str(e)}")
            
            # 过滤掉数量为0的资产
            purchased_assets = [asset for asset in purchased_assets if asset.get('quantity', 0) > 0]
            
            logger.info(f"最终找到 {len(purchased_assets)} 个有效购买资产")
            
            # 对资产按拥有数量排序，数量多的排在前面
            purchased_assets.sort(key=lambda x: x.get('quantity', 0), reverse=True)
            
            return purchased_assets
            
        except Exception as e:
            logger.exception(f"获取用户资产列表异常: {str(e)}")
            return [] 

    @staticmethod
    def calculate_unlimited_commission(wallet_address, max_levels=999):
        """
        计算无限级分销佣金
        上级得到的佣金 = 下级直接购买金额的35% + 下级得到的所有佣金收入的35%
        
        Args:
            wallet_address: 钱包地址
            max_levels: 最大层级数，999表示无限级
            
        Returns:
            dict: {
                'total_commission': 总佣金,
                'direct_commission': 直接推荐佣金,
                'indirect_commission': 间接推荐佣金,
                'level_details': 各层级详情
            }
        """
        logger.warning("calculate_unlimited_commission 功能已临时禁用以修复启动错误。")
        return {
            'total_commission': 0.0,
            'direct_commission': 0.0,
            'indirect_commission': 0.0,
            'level_details': {},
            'error': '此功能正在重构中，暂时不可用。'
        }
    
    @staticmethod
    def update_commission_balance(wallet_address):
        """
        更新用户佣金余额到数据库
        使用新的无限级分销计算逻辑
        """
        logger.warning("update_commission_balance 功能已临时禁用以修复启动错误。")
        return None

    @staticmethod
    def get_commission_balance(wallet_address):
        """
        获取用户的交易总佣金（简化版本）
        """
        logger.warning("get_commission_balance 功能已临时禁用以修复启动错误。")
        return 0.0

    @staticmethod
    def get_ethereum_usdc_balance(wallet_address):
        """
        获取以太坊网络的USDC余额（服务器代理方式）
        
        Args:
            wallet_address: 以太坊钱包地址
            
        Returns:
            float: USDC余额
        """
        logger.warning("get_ethereum_usdc_balance 功能已临时禁用以修复启动错误。")
        return 0.0

    @staticmethod
    def get_solana_usdc_balance(wallet_address):
        """
        获取Solana网络的USDC余额（服务器代理方式）
        
        Args:
            wallet_address: Solana钱包地址
            
        Returns:
            float: USDC余额
        """
        logger.warning("get_solana_usdc_balance 功能已临时禁用以修复启动错误。")
        return 0.0 

    @staticmethod
    def register_wallet_user(wallet_address, wallet_type='ethereum'):
        """
        钱包连接时自动注册/更新用户信息
        
        Args:
            wallet_address: 钱包地址
            wallet_type: 钱包类型 ('ethereum', 'phantom', 'solana')
        
        Returns:
            dict: 用户信息
        """
        try:
            from app.models import User, db
            from datetime import datetime
            from flask import current_app
            from app.models.commission_config import CommissionConfig
            
            # 标准化钱包地址
            wallet_address = wallet_address.strip()
            
            # 检查是否启用平台推荐人功能
            enable_platform_referrer = CommissionConfig.get_config('enable_platform_referrer', True)
            platform_referrer_address = CommissionConfig.get_config('platform_referrer_address', '')
            
            # 根据钱包类型设置相应的地址字段
            if wallet_type in ['phantom', 'solana']:
                # Solana钱包
                user = User.query.filter_by(solana_address=wallet_address).first()
                
                if not user:
                    # 使用钱包地址生成简单的用户名和邮箱（无需时间戳，因为钱包地址本身就是唯一的）
                    username = f"solana_{wallet_address[:8]}"
                    email = f"{wallet_address}@solana.wallet"
                    
                    # 创建新用户
                    user = User(
                        username=username,
                        email=email,
                        solana_address=wallet_address,
                        wallet_type=wallet_type,
                        created_at=datetime.utcnow(),
                        last_login_at=datetime.utcnow(),
                        is_active=True
                    )
                    
                    # 自动设置平台推荐人（如果启用且配置了平台地址）
                    if enable_platform_referrer and platform_referrer_address and platform_referrer_address != wallet_address:
                        user.referrer_address = platform_referrer_address
                        current_app.logger.info(f"新Solana用户 {wallet_address} 自动设置平台推荐人: {platform_referrer_address}")
                    
                    db.session.add(user)
                    current_app.logger.info(f"创建新Solana用户: {wallet_address}")
                else:
                    # 更新现有用户（同一钱包地址的重复连接）
                    user.last_login_at = datetime.utcnow()
                    user.wallet_type = wallet_type
                    user.is_active = True
                    
                    # 如果用户还没有推荐人，且启用了平台推荐人功能，自动设置
                    if (not user.referrer_address and enable_platform_referrer and 
                        platform_referrer_address and platform_referrer_address != wallet_address):
                        user.referrer_address = platform_referrer_address
                        current_app.logger.info(f"现有Solana用户 {wallet_address} 自动设置平台推荐人: {platform_referrer_address}")
                    
                    current_app.logger.info(f"更新现有Solana用户: {wallet_address}")
                    
            else:
                # 以太坊钱包
                user = User.query.filter_by(eth_address=wallet_address).first()
                
                if not user:
                    # 使用钱包地址生成简单的用户名和邮箱（无需时间戳，因为钱包地址本身就是唯一的）
                    username = f"eth_{wallet_address[:8]}"
                    email = f"{wallet_address}@ethereum.wallet"
                    
                    # 创建新用户
                    user = User(
                        username=username,
                        email=email,
                        eth_address=wallet_address,
                        wallet_type=wallet_type,
                        created_at=datetime.utcnow(),
                        last_login_at=datetime.utcnow(),
                        is_active=True
                    )
                    
                    # 自动设置平台推荐人（如果启用且配置了平台地址）
                    if enable_platform_referrer and platform_referrer_address and platform_referrer_address != wallet_address:
                        user.referrer_address = platform_referrer_address
                        current_app.logger.info(f"新以太坊用户 {wallet_address} 自动设置平台推荐人: {platform_referrer_address}")
                    
                    db.session.add(user)
                    current_app.logger.info(f"创建新以太坊用户: {wallet_address}")
                else:
                    # 更新现有用户（同一钱包地址的重复连接）
                    user.last_login_at = datetime.utcnow()
                    user.wallet_type = wallet_type
                    user.is_active = True
                    
                    # 如果用户还没有推荐人，且启用了平台推荐人功能，自动设置
                    if (not user.referrer_address and enable_platform_referrer and 
                        platform_referrer_address and platform_referrer_address != wallet_address):
                        user.referrer_address = platform_referrer_address
                        current_app.logger.info(f"现有以太坊用户 {wallet_address} 自动设置平台推荐人: {platform_referrer_address}")
                    
                    current_app.logger.info(f"更新现有以太坊用户: {wallet_address}")
            
            # 提交数据库更改
            db.session.commit()
            
            # 返回用户信息
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'eth_address': user.eth_address,
                'solana_address': user.solana_address,
                'wallet_type': user.wallet_type,
                'referrer_address': user.referrer_address,  # 添加推荐人地址到返回信息
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                'is_active': user.is_active
            }
            
        except Exception as e:
            current_app.logger.error(f"注册钱包用户失败: {str(e)}")
            # 回滚数据库更改
            try:
                db.session.rollback()
            except:
                pass
            raise e 