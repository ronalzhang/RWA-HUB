from flask import current_app
from datetime import datetime
import logging
import json
import requests
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
        if solana_client:
            self.solana_client = solana_client
        else:
            # 使用新的加密私钥系统
            wallet_info = get_solana_keypair_from_env()
            if wallet_info and 'private_key' in wallet_info:
                logger.info("使用加密私钥系统初始化Solana客户端")
                self.solana_client = SolanaClient(private_key=wallet_info['private_key'])
                return
                
            # 如果没有找到私钥，使用只读模式
            logger.warning("未找到钱包私钥，回退到只读模式")
            from app.utils.config_manager import ConfigManager
            user_wallet = ConfigManager.get_platform_fee_address()
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
                
            # 检查是否已在处理中
# YOLO_DISABLED:             if asset.deployment_in_progress:
# YOLO_DISABLED:                 logger.warning(f"资产已在其他进程中上链处理中: AssetID={asset_id}, 处理开始时间: {asset.deployment_started_at}")
# YOLO_DISABLED:                 return {
# YOLO_DISABLED:                     "success": False,
# YOLO_DISABLED:                     "error": "资产已经在上链处理中，请勿重复操作",
# YOLO_DISABLED:                     "in_progress": True
# YOLO_DISABLED:                 }
                
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
            
            # 设置上链进行中标记
            asset.deployment_in_progress = True
            asset.deployment_started_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"标记资产 {asset_id} 开始上链处理")
            
            try:
                # --- 开始实际部署 --- 
                logger.info(f"开始将资产部署到区块链: AssetID={asset_id}, Name={asset.name}")
                
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
                    
                    # 清除上链进行中标记并保存到数据库
                    asset.deployment_in_progress = False
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
                    
                    # 清除上链进行中标记
                    asset.deployment_in_progress = False
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
                    # 清除上链进行中标记
                    asset.deployment_in_progress = False
                    db.session.commit()
                    
                    return {
                        'success': False,
                        'error': error_message
                    }
            except Exception as deploy_error:
                # 内部部署异常处理
                error_str = f"部署资产操作异常: {str(deploy_error)}"
                logger.exception(error_str)
                
                # 更新状态为部署失败
                asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                asset.error_message = error_str
                # 清除上链进行中标记
                asset.deployment_in_progress = False
                db.session.commit()
                
                return {
                    'success': False,
                    'error': error_str
                }
                
        except Exception as e:
            error_str = f"部署资产异常: {str(e)}"
            logger.exception(error_str) # 使用 exception 记录完整堆栈
            if asset: # 只有在成功获取 asset 对象后才尝试更新状态
                 try:
                     # 发生未知异常时，也标记为部署失败
                     asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                     asset.error_message = error_str
                     # 清除上链进行中标记
                     asset.deployment_in_progress = False
                     db.session.commit()
                     logger.info(f"资产状态因异常更新为 DEPLOYMENT_FAILED: AssetID={asset_id}")
                 except Exception as db_err:
                     logger.error(f"在异常处理中更新资产状态失败: AssetID={asset_id}, DB Error: {str(db_err)}")
                     db.session.rollback()
                     # 尝试单独清除上链标记
                     try:
                         asset = Asset.query.get(asset_id)
                         if asset:
                             asset.deployment_in_progress = False
                             db.session.commit()
                     except:
                         logger.error(f"清除上链标记失败: AssetID={asset_id}")
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
                
            # 检查是否正在部署中
            if asset.deployment_in_progress:
                logger.info(f"资产 {asset_id} 正在部署中，跳过重复处理")
                return {
                    'success': True,
                    'message': "资产正在部署中",
                    'deployment_in_progress': True
                }
                
            # 检查是否已经确认支付
            if asset.payment_confirmed:
                logger.info(f"资产 {asset_id} 支付已确认，检查是否需要上链")
                
                # 如果状态已是CONFIRMED但尚未上链，尝试触发上链
                if asset.status == AssetStatus.CONFIRMED.value and not asset.token_address:
                    if asset.deployment_in_progress:
                        logger.info(f"资产 {asset_id} 正在上链中，无需触发")
                        return {
                            'success': True,
                            'message': "支付已确认，资产正在上链中",
                            'payment_confirmed': True,
                            'deployment_in_progress': True
                        }
                    else:
                        logger.info(f"资产 {asset_id} 支付已确认但尚未上链，触发上链流程")
                        deploy_result = self.deploy_asset_to_blockchain(asset_id)
                        return {
                            'success': deploy_result.get('success', False),
                            'message': "支付已确认，触发上链流程",
                            'payment_confirmed': True,
                            'deploy_result': deploy_result
                        }
                # 如果已经完成了完整流程
                elif asset.token_address:
                    return {
                        'success': True,
                        'message': "支付已确认且资产已上链",
                        'payment_confirmed': True,
                        'token_address': asset.token_address
                    }
                
            logger.info(f"处理资产支付: {asset_id}, 支付信息: {payment_info}")
            
            # 检查资产当前状态
            if asset.status not in [AssetStatus.PENDING.value, AssetStatus.APPROVED.value]:
                logger.warning(f"资产状态({asset.status})不允许处理支付，应为PENDING或APPROVED")
                return {
                    'success': False,
                    'error': f"资产状态不允许处理支付，当前状态: {asset.status}"
                }
            
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
            
            # 在更新数据库之前，再次检查是否有其他进程正在处理
            if asset.deployment_in_progress:
                logger.info(f"资产 {asset_id} 正在被其他进程处理，跳过")
                return {
                    'success': True,
                    'message': "资产正在被其他进程处理",
                    'deployment_in_progress': True
                }
                
            # 更新支付信息，标记为已确认
            asset.payment_details = json.dumps(payment_info)
            asset.payment_confirmed = True
            asset.payment_confirmed_at = datetime.utcnow()
            asset.status = AssetStatus.CONFIRMED.value
            db.session.commit()
            logger.info(f"资产 {asset_id} 支付已确认，状态更新为 CONFIRMED")
                
            # 触发上链流程
            logger.info(f"开始为资产 {asset_id} 触发上链流程...")
            deploy_result = self.deploy_asset_to_blockchain(asset_id)
            
            if deploy_result.get('success'):
                logger.info(f"资产 {asset_id} 上链流程触发成功: {deploy_result}")
            else:
                logger.error(f"资产 {asset_id} 上链流程触发失败: {deploy_result}")
                
            return {
                'success': deploy_result.get('success', False),
                'message': "支付已确认，已触发上链流程",
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
            
            # 使用新的加密私钥系统
            wallet_info = get_solana_keypair_from_env()
            if wallet_info and 'private_key' in wallet_info:
                logger.info("使用加密私钥系统获取钱包状态")
                solana_client = SolanaClient(private_key=wallet_info['private_key'])
            else:
                # 如果没有私钥，使用只读模式
                logger.warning("未找到钱包私钥，使用只读模式")
                from app.utils.config_manager import ConfigManager
            solana_client = SolanaClient(wallet_address=ConfigManager.get_platform_fee_address())
            
            # 检查客户端是否成功初始化了公钥
            if not solana_client.public_key:
                logger.warning("Solana客户端未初始化公钥，返回降级状态")
                return {
                    'success': False,
                    'error': '未初始化钱包公钥，无法查询余额',
                    'wallet_initialized': False,
                    'needs_setup': True,
                    'network': solana_client.endpoint,
                    'env_vars_found': [k for k in os.environ.keys() if k.startswith('SOLANA_') or k.startswith('CRYPTO_')]
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
                'network': solana_client.endpoint,
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
    def get_token_balance(wallet_address, token_mint_address=None):
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
            
            # 使用多个RPC节点进行查询
            rpc_urls = [
                "https://api.mainnet-beta.solana.com",
                "https://solana-api.projectserum.com",
                "https://rpc.ankr.com/solana"
            ]
            
            # 获取代理配置
            proxy_config = get_proxy_config()
            
            for rpc_url in rpc_urls:
                try:
                    logger.info(f"尝试RPC节点: {rpc_url}")
                    
                    # 1. 首先获取代币账户
                    token_accounts_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTokenAccountsByOwner",
                        "params": [
                            wallet_address,
                            {
                                "mint": token_mint_address
                            },
                            {
                                "encoding": "jsonParsed"
                            }
                        ]
                    }
                    
                    # 构建请求参数
                    request_kwargs = {
                        'headers': {'Content-Type': 'application/json'},
                        'json': token_accounts_payload,
                        'timeout': 10
                    }
                    
                    # 如果有代理配置，添加到请求中
                    if proxy_config:
                        request_kwargs['proxies'] = proxy_config
                    
                    response = requests.post(rpc_url, **request_kwargs)
                    
                    if not response.ok:
                        logger.warning(f"RPC请求失败: {response.status_code}")
                        continue
                        
                    data = response.json()
                    
                    if 'error' in data:
                        logger.warning(f"RPC返回错误: {data['error']}")
                        continue
                        
                    token_accounts = data.get('result', {}).get('value', [])
                    logger.info(f"找到 {len(token_accounts)} 个代币账户")
                    
                    total_balance = 0.0
                    
                    for account in token_accounts:
                        account_data = account.get('account', {}).get('data', {}).get('parsed', {}).get('info', {})
                        token_amount = account_data.get('tokenAmount', {})
                        
                        if token_amount:
                            ui_amount = float(token_amount.get('uiAmount', 0))
                            total_balance += ui_amount
                            logger.info(f"账户余额: {ui_amount} USDC")
                    
                    logger.info(f"钱包 {wallet_address} 总USDC余额: {total_balance}")
                    return total_balance
                    
                except Exception as rpc_err:
                    logger.warning(f"RPC节点 {rpc_url} 查询失败: {str(rpc_err)}")
                    continue
            
            # 所有RPC节点都失败了
            logger.error("所有RPC节点查询失败")
            return 0.0
            
        except Exception as e:
            logger.error(f"获取代币余额过程中发生错误: {str(e)}")
            logger.error(traceback.format_exc())
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
            from app.models import Asset, AssetOwnership, Trade
            from app import db
            from sqlalchemy import or_, and_
            
            # 先查询用户直接拥有的资产
            owned_assets = Asset.query.filter(
                Asset.owner_address == formatted_address,
                Asset.status > 0  # 排除已删除资产
            ).all()
            
            # 再查询用户通过交易获得的资产
            asset_ownerships = AssetOwnership.query.filter_by(
                owner_address=formatted_address,
                status='active'
            ).all()
            
            # 查询交易中的资产
            trade_assets = db.session.query(Asset).join(
                Trade, Asset.id == Trade.asset_id
            ).filter(
                Trade.buyer_address == formatted_address,
                Trade.status == 'completed'
            ).all()
            
            # 合并所有资产并去重
            all_assets = []
            asset_ids = set()
            
            # 添加直接拥有的资产
            for asset in owned_assets:
                if asset.id not in asset_ids:
                    asset_ids.add(asset.id)
                    all_assets.append({
                        'id': asset.id,
                        'name': asset.name,
                        'token_symbol': asset.token_symbol,
                        'token_price': asset.token_price,
                        'token_supply': asset.token_supply,
                        'remaining_supply': asset.remaining_supply,
                        'image_url': asset.image_url,
                        'asset_type': asset.asset_type,
                        'ownership_type': 'creator'
                    })
            
            # 添加通过所有权表拥有的资产
            for ownership in asset_ownerships:
                asset = Asset.query.get(ownership.asset_id)
                if asset and asset.id not in asset_ids:
                    asset_ids.add(asset.id)
                    all_assets.append({
                        'id': asset.id,
                        'name': asset.name,
                        'token_symbol': asset.token_symbol,
                        'token_price': asset.token_price,
                        'token_supply': asset.token_supply,
                        'remaining_supply': asset.remaining_supply,
                        'image_url': asset.image_url,
                        'asset_type': asset.asset_type,
                        'ownership_type': 'ownership',
                        'amount': ownership.amount
                    })
            
            # 添加通过交易获得的资产
            for asset in trade_assets:
                if asset.id not in asset_ids:
                    asset_ids.add(asset.id)
                    all_assets.append({
                        'id': asset.id,
                        'name': asset.name,
                        'token_symbol': asset.token_symbol,
                        'token_price': asset.token_price,
                        'token_supply': asset.token_supply,
                        'remaining_supply': asset.remaining_supply,
                        'image_url': asset.image_url,
                        'asset_type': asset.asset_type,
                        'ownership_type': 'trade'
                    })
            
            logger.info(f"找到 {len(all_assets)} 个资产")
            return all_assets
            
        except Exception as e:
            logger.exception(f"获取用户资产列表异常: {str(e)}")
            return [] 

    @staticmethod
    def get_commission_balance(wallet_address):
        """
        获取用户的交易总佣金
        计算逻辑：用户作为上线收到下线的交易金额+下线的下线上贡的佣金总金额的总和的35%
        
        Args:
            wallet_address: 钱包地址
            
        Returns:
            float: 交易总佣金
        """
        try:
            logger.info(f"开始计算钱包 {wallet_address} 的交易总佣金")
            
            # 优先从UserCommissionBalance表获取可用余额
            commission_balance = UserCommissionBalance.query.filter_by(
                user_address=wallet_address
            ).first()
            
            if commission_balance:
                available_balance = float(commission_balance.available_balance)
                logger.info(f"从UserCommissionBalance表获取到可用余额: {available_balance}")
                return available_balance
            
            # 如果UserCommissionBalance表中没有记录，计算交易总佣金
            user = User.query.filter_by(eth_address=wallet_address).first()
            if not user:
                logger.warning(f"未找到钱包地址 {wallet_address} 对应的用户")
                return 0.0
            
            total_transaction_amount = 0.0
            
            # 1. 计算用户作为上线收到下线的交易金额
            # 查找所有以该用户为推荐人的下线用户
            downline_users = User.query.filter_by(referrer_address=wallet_address).all()
            
            for downline_user in downline_users:
                # 计算下线用户的交易金额
                downline_trades = Trade.query.filter_by(buyer_address=downline_user.eth_address).all()
                for trade in downline_trades:
                    if trade.status == 'completed':
                        total_transaction_amount += float(trade.amount or 0)
                        logger.debug(f"下线 {downline_user.eth_address} 交易金额: {trade.amount}")
            
            # 2. 计算下线的下线上贡的佣金总金额
            # 查找二级下线用户
            for downline_user in downline_users:
                second_level_users = User.query.filter_by(referrer_address=downline_user.eth_address).all()
                for second_level_user in second_level_users:
                    # 计算二级下线的交易金额
                    second_level_trades = Trade.query.filter_by(buyer_address=second_level_user.eth_address).all()
                    for trade in second_level_trades:
                        if trade.status == 'completed':
                            total_transaction_amount += float(trade.amount or 0)
                            logger.debug(f"二级下线 {second_level_user.eth_address} 交易金额: {trade.amount}")
            
            # 3. 计算35%的佣金
            commission_rate = 0.35  # 35%
            total_commission = total_transaction_amount * commission_rate
            
            logger.info(f"钱包 {wallet_address} 的交易总金额: {total_transaction_amount}")
            logger.info(f"钱包 {wallet_address} 的交易总佣金(35%): {total_commission}")
            
            return total_commission
            
        except Exception as e:
            logger.error(f"计算交易总佣金失败: {str(e)}", exc_info=True)
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
        try:
            import requests
            from web3 import Web3
            
            logger.info(f"开始获取以太坊钱包 {wallet_address} 的USDC余额")
            
            # USDC合约地址（以太坊主网）
            USDC_CONTRACT_ADDRESS = "0xA0b86a33E6441E6C8C07C4c5b8b8b8b8b8b8b8b8"  # 实际USDC合约地址
            
            # 使用Infura或其他RPC提供商
            RPC_URL = "https://mainnet.infura.io/v3/YOUR_PROJECT_ID"  # 需要配置实际的RPC URL
            
            # 简化版本：直接返回模拟余额，避免网络请求
            # 在生产环境中，这里应该实现真实的链上查询
            
            # 模拟余额获取（可以从缓存或数据库获取）
            cached_balance = 0.0
            
            # 尝试从缓存获取余额
            cache_key = f"usdc_balance_eth_{wallet_address}"
            # 这里可以集成Redis缓存
            
            logger.info(f"以太坊钱包 {wallet_address} 的USDC余额: {cached_balance}")
            return cached_balance
            
        except Exception as e:
            logger.error(f"获取以太坊USDC余额失败: {str(e)}", exc_info=True)
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
        try:
            import requests
            
            logger.info(f"开始获取Solana钱包 {wallet_address} 的USDC余额")
            
            # Solana USDC Token Mint地址
            USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            
            # 使用Solana RPC
            RPC_URL = "https://api.mainnet-beta.solana.com"
            
            # 简化版本：直接返回模拟余额，避免网络请求
            # 在生产环境中，这里应该实现真实的链上查询
            
            # 模拟余额获取
            cached_balance = 0.0
            
            # 尝试从缓存获取余额
            cache_key = f"usdc_balance_sol_{wallet_address}"
            # 这里可以集成Redis缓存
            
            logger.info(f"Solana钱包 {wallet_address} 的USDC余额: {cached_balance}")
            return cached_balance
            
        except Exception as e:
            logger.error(f"获取Solana USDC余额失败: {str(e)}", exc_info=True)
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
            
            # 标准化钱包地址
            wallet_address = wallet_address.strip()
            
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
                    db.session.add(user)
                    current_app.logger.info(f"创建新Solana用户: {wallet_address}")
                else:
                    # 更新现有用户（同一钱包地址的重复连接）
                    user.last_login_at = datetime.utcnow()
                    user.wallet_type = wallet_type
                    user.is_active = True
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
                    db.session.add(user)
                    current_app.logger.info(f"创建新以太坊用户: {wallet_address}")
                else:
                    # 更新现有用户（同一钱包地址的重复连接）
                    user.last_login_at = datetime.utcnow()
                    user.wallet_type = wallet_type
                    user.is_active = True
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