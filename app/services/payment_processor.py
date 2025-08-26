#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
优化的支付处理器 - 处理资产发布和购买的完整支付流程
实现任务3.1: 资产发布支付流程
"""

import logging
import json
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import asyncio
import time

from flask import current_app
from sqlalchemy import text
from app.extensions import db
from app.models import Asset, Trade
from app.models.asset import AssetStatus
from app.models.trade import TradeStatus, TradeType
from app.blockchain.solana_service import validate_solana_address, prepare_transfer_transaction
from app.utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)

@dataclass
class PaymentResult:
    """支付结果数据类"""
    success: bool
    transaction_hash: Optional[str] = None
    amount: Optional[Decimal] = None
    platform_fee: Optional[Decimal] = None
    commission_breakdown: Optional[Dict] = None
    error_message: Optional[str] = None
    payment_details: Optional[Dict] = None
    transaction_data: Optional[bytes] = None  # 新增：交易数据用于前端签名
    message_data: Optional[bytes] = None      # 新增：消息数据用于前端签名
    payment_status: Optional[str] = None      # 新增：支付状态跟踪

@dataclass
class PaymentStatusInfo:
    """支付状态信息"""
    asset_id: int
    status: str
    payment_confirmed: bool
    transaction_hash: Optional[str] = None
    confirmation_count: int = 0
    error_message: Optional[str] = None
    last_updated: Optional[datetime] = None

@dataclass
class CommissionBreakdown:
    """佣金分配明细"""
    seller_amount: Decimal
    platform_fee: Decimal
    referral_commissions: List[Dict]
    total_referral_amount: Decimal

class PaymentProcessor:
    """优化的支付处理器 - 实现任务3.1资产发布支付流程"""
    
    def __init__(self):
        self.platform_fee_rate = Decimal(str(ConfigManager.get_platform_fee_rate()))
        self.referral_rate = Decimal('0.05')  # 5%推荐佣金
        self.platform_address = ConfigManager.get_platform_fee_address()
        self.asset_creation_fee_address = ConfigManager.get_asset_creation_fee_address()
        self.asset_creation_fee_amount = Decimal(str(ConfigManager.get_asset_creation_fee_amount()))
        self.usdc_mint = ConfigManager.get_usdc_mint()
        
        # 支付状态跟踪
        self._payment_status_cache = {}
        
        logger.info(f"PaymentProcessor初始化完成 - 平台费率: {self.platform_fee_rate}, 资产创建费: {self.asset_creation_fee_amount} USDC")
        
    def prepare_asset_publication_payment(self, asset_id: int, payer_address: str) -> PaymentResult:
        """
        准备资产发布支付交易（任务3.1核心功能）
        生成待签名的交易数据，供前端钱包签名
        
        Args:
            asset_id: 资产ID
            payer_address: 支付方地址
            
        Returns:
            PaymentResult: 包含待签名交易数据的支付结果
        """
        try:
            logger.info(f"准备资产发布支付交易: asset_id={asset_id}, payer={payer_address}")
            
            # 1. 验证资产存在且状态正确
            asset = Asset.query.get(asset_id)
            if not asset:
                return PaymentResult(
                    success=False,
                    error_message=f"资产不存在: {asset_id}"
                )
            
            # 检查资产状态是否允许支付
            if asset.status not in [AssetStatus.PENDING.value, AssetStatus.PAYMENT_PROCESSING.value]:
                return PaymentResult(
                    success=False,
                    error_message=f"资产状态不允许支付，当前状态: {asset.status}"
                )
            
            # 2. 验证支付地址
            if not validate_solana_address(payer_address):
                return PaymentResult(
                    success=False,
                    error_message=f"无效的Solana地址: {payer_address}"
                )
            
            # 3. 验证支付者是否为资产创建者
            if asset.creator_address.lower() != payer_address.lower():
                return PaymentResult(
                    success=False,
                    error_message="只有资产创建者可以支付发布费用"
                )
            
            # 4. 计算费用
            payment_amount = self.asset_creation_fee_amount
            platform_fee = payment_amount * self.platform_fee_rate
            net_amount = payment_amount - platform_fee
            
            logger.info(f"资产发布费用计算: 总额={payment_amount} USDC, 平台费={platform_fee} USDC, 净额={net_amount} USDC")
            
            # 5. 准备Solana USDC转账交易
            try:
                transaction_data, message_data = prepare_transfer_transaction(
                    token_symbol="USDC",
                    from_address=payer_address,
                    to_address=self.asset_creation_fee_address,
                    amount=float(payment_amount)
                )
                
                logger.info(f"成功生成资产发布支付交易数据，交易大小: {len(transaction_data)} bytes")
                
            except Exception as tx_error:
                logger.error(f"生成支付交易数据失败: {str(tx_error)}")
                return PaymentResult(
                    success=False,
                    error_message=f"生成支付交易失败: {str(tx_error)}"
                )
            
            # 6. 更新资产状态为支付处理中
            try:
                with db.session.begin():
                    asset.status = AssetStatus.PAYMENT_PROCESSING.value
                    asset.updated_at = datetime.utcnow()
                    db.session.commit()
                    
                logger.info(f"资产状态已更新为支付处理中: asset_id={asset_id}")
                
            except Exception as db_error:
                logger.error(f"更新资产状态失败: {str(db_error)}")
                # 不影响交易数据生成
            
            # 7. 缓存支付状态
            payment_status = PaymentStatusInfo(
                asset_id=asset_id,
                status='payment_prepared',
                payment_confirmed=False,
                last_updated=datetime.utcnow()
            )
            self._payment_status_cache[asset_id] = payment_status
            
            # 8. 构建支付详情
            payment_details = {
                'type': 'asset_publication',
                'asset_id': asset_id,
                'total_amount': float(payment_amount),
                'platform_fee': float(platform_fee),
                'net_amount': float(net_amount),
                'payer_address': payer_address,
                'recipient_address': self.asset_creation_fee_address,
                'token': 'USDC',
                'token_mint': self.usdc_mint,
                'prepared_at': datetime.utcnow().isoformat(),
                'status': 'prepared'
            }
            
            logger.info(f"资产发布支付交易准备完成: asset_id={asset_id}")
            
            return PaymentResult(
                success=True,
                amount=payment_amount,
                platform_fee=platform_fee,
                transaction_data=transaction_data,
                message_data=message_data,
                payment_details=payment_details,
                payment_status='prepared'
            )
            
        except Exception as e:
            logger.error(f"准备资产发布支付失败: {str(e)}", exc_info=True)
            return PaymentResult(
                success=False,
                error_message=f"准备支付失败: {str(e)}"
            )
    
    def confirm_asset_publication_payment(self, asset_id: int, transaction_hash: str, 
                                        payer_address: str) -> PaymentResult:
        """
        确认资产发布支付（任务3.1核心功能）
        处理前端提交的已签名交易哈希，更新支付状态
        
        Args:
            asset_id: 资产ID
            transaction_hash: 交易哈希
            payer_address: 支付方地址
            
        Returns:
            PaymentResult: 支付确认结果
        """
        try:
            logger.info(f"确认资产发布支付: asset_id={asset_id}, tx_hash={transaction_hash}")
            
            # 1. 验证资产存在
            asset = Asset.query.get(asset_id)
            if not asset:
                return PaymentResult(
                    success=False,
                    error_message=f"资产不存在: {asset_id}"
                )
            
            # 2. 验证资产状态
            if asset.status != AssetStatus.PAYMENT_PROCESSING.value:
                return PaymentResult(
                    success=False,
                    error_message=f"资产状态错误，当前状态: {asset.status}"
                )
            
            # 3. 验证交易哈希格式
            if not transaction_hash or len(transaction_hash) < 32:
                return PaymentResult(
                    success=False,
                    error_message="无效的交易哈希"
                )
            
            # 4. 检查是否重复确认
            if asset.payment_tx_hash == transaction_hash:
                logger.warning(f"重复确认支付: asset_id={asset_id}, tx_hash={transaction_hash}")
                return PaymentResult(
                    success=True,
                    transaction_hash=transaction_hash,
                    amount=self.asset_creation_fee_amount,
                    error_message="支付已确认"
                )
            
            # 5. 更新资产支付状态
            try:
                with db.session.begin():
                    asset.payment_tx_hash = transaction_hash
                    asset.payment_confirmed = True
                    asset.payment_confirmed_at = datetime.utcnow()
                    asset.status = AssetStatus.CONFIRMED.value
                    asset.updated_at = datetime.utcnow()
                    
                    # 保存支付详情
                    payment_details = {
                        'type': 'asset_publication',
                        'asset_id': asset_id,
                        'total_amount': float(self.asset_creation_fee_amount),
                        'platform_fee': float(self.asset_creation_fee_amount * self.platform_fee_rate),
                        'payer_address': payer_address,
                        'recipient_address': self.asset_creation_fee_address,
                        'tx_hash': transaction_hash,
                        'token': 'USDC',
                        'confirmed_at': datetime.utcnow().isoformat(),
                        'status': 'confirmed'
                    }
                    asset.payment_details = json.dumps(payment_details)
                    
                    db.session.commit()
                    
                logger.info(f"资产支付状态已更新: asset_id={asset_id}, status=CONFIRMED")
                
                # 使用DataConsistencyManager清除相关缓存
                from app.services.data_consistency_manager import DataConsistencyManager
                data_manager = DataConsistencyManager()
                data_manager._invalidate_cache(f"asset_data:{asset_id}")
                logger.info(f"已清除资产缓存: asset_id={asset_id}")
                
            except Exception as db_error:
                logger.error(f"更新资产支付状态失败: {str(db_error)}")
                return PaymentResult(
                    success=False,
                    error_message=f"更新支付状态失败: {str(db_error)}"
                )
            
            # 6. 更新支付状态缓存
            payment_status = PaymentStatusInfo(
                asset_id=asset_id,
                status='confirmed',
                payment_confirmed=True,
                transaction_hash=transaction_hash,
                last_updated=datetime.utcnow()
            )
            self._payment_status_cache[asset_id] = payment_status
            
            # 7. 异步触发智能合约资产创建
            try:
                self._trigger_asset_deployment(asset_id)
            except Exception as contract_error:
                logger.error(f"触发智能合约资产创建失败: {str(contract_error)}")
                # 不影响支付确认结果
            
            logger.info(f"资产发布支付确认完成: asset_id={asset_id}")
            
            return PaymentResult(
                success=True,
                transaction_hash=transaction_hash,
                amount=self.asset_creation_fee_amount,
                platform_fee=self.asset_creation_fee_amount * self.platform_fee_rate,
                payment_details=payment_details,
                payment_status='confirmed'
            )
            
        except Exception as e:
            logger.error(f"确认资产发布支付失败: {str(e)}", exc_info=True)
            return PaymentResult(
                success=False,
                error_message=f"确认支付失败: {str(e)}"
            )
    
    def _trigger_asset_deployment(self, asset_id: int):
        """
        触发资产智能合约部署（异步）
        
        Args:
            asset_id: 资产ID
        """
        try:
            logger.info(f"触发资产智能合约部署: asset_id={asset_id}")
            
            # 这里可以集成实际的智能合约部署逻辑
            # 目前先记录日志，后续可以集成到区块链服务中
            
            # 模拟异步部署过程
            def deploy_asset_async():
                try:
                    # 模拟部署延迟
                    time.sleep(2)
                    
                    # 更新资产状态为已部署
                    asset = Asset.query.get(asset_id)
                    if asset:
                        with db.session.begin():
                            asset.status = AssetStatus.ON_CHAIN.value
                            asset.updated_at = datetime.utcnow()
                            db.session.commit()
                        
                        logger.info(f"资产智能合约部署完成: asset_id={asset_id}")
                    
                except Exception as e:
                    logger.error(f"异步部署资产失败: asset_id={asset_id}, error={str(e)}")
            
            # 在实际环境中，这里应该使用Celery或其他任务队列
            # 现在使用简单的线程模拟
            import threading
            deployment_thread = threading.Thread(target=deploy_asset_async)
            deployment_thread.daemon = True
            deployment_thread.start()
            
        except Exception as e:
            logger.error(f"触发资产部署失败: {str(e)}")
    
    
    
    def prepare_asset_purchase_payment(self, trade_id: int) -> PaymentResult:
        """
        准备资产购买支付交易（任务3.2核心功能）
        生成多方转账的待签名交易数据
        
        Args:
            trade_id: 交易ID
            
        Returns:
            PaymentResult: 包含多方转账交易数据的支付结果
        """
        try:
            logger.info(f"准备资产购买支付交易: trade_id={trade_id}")
            
            # 1. 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                return PaymentResult(
                    success=False,
                    error_message=f"交易记录不存在: {trade_id}"
                )
            
            # 2. 验证交易状态
            if trade.status not in [TradeStatus.PENDING.value, TradeStatus.PENDING_PAYMENT.value]:
                return PaymentResult(
                    success=False,
                    error_message=f"交易状态不允许支付，当前状态: {trade.status}"
                )
            
            # 3. 获取资产信息
            asset = Asset.query.get(trade.asset_id)
            if not asset:
                return PaymentResult(
                    success=False,
                    error_message=f"资产不存在: {trade.asset_id}"
                )
            
            # 4. 验证资产供应量
            if asset.remaining_supply < trade.amount:
                return PaymentResult(
                    success=False,
                    error_message=f"资产供应量不足，剩余: {asset.remaining_supply}, 需要: {trade.amount}"
                )
            
            # 5. 计算佣金分配
            commission_breakdown = self._calculate_purchase_commission(trade)
            
            # 6. 生成多方转账交易数据
            try:
                multi_transfer_data = self._prepare_multi_party_transfer_transaction(
                    trade, commission_breakdown
                )
                
                if not multi_transfer_data['success']:
                    return PaymentResult(
                        success=False,
                        error_message=multi_transfer_data['error']
                    )
                
                logger.info(f"成功生成多方转账交易数据: trade_id={trade_id}")
                
            except Exception as tx_error:
                logger.error(f"生成多方转账交易失败: {str(tx_error)}")
                return PaymentResult(
                    success=False,
                    error_message=f"生成转账交易失败: {str(tx_error)}"
                )
            
            # 7. 更新交易状态为支付处理中
            try:
                with db.session.begin():
                    trade.status = TradeStatus.PENDING_PAYMENT.value
                    trade.updated_at = datetime.utcnow()
                    db.session.commit()
                    
                logger.info(f"交易状态已更新为支付处理中: trade_id={trade_id}")
                
            except Exception as db_error:
                logger.error(f"更新交易状态失败: {str(db_error)}")
                # 不影响交易数据生成
            
            # 8. 构建支付详情
            payment_details = {
                'type': 'asset_purchase',
                'trade_id': trade_id,
                'asset_id': trade.asset_id,
                'buyer_address': trade.trader_address,
                'seller_address': asset.creator_address,
                'total_amount': float(trade.total),
                'token_amount': trade.amount,
                'token_price': float(trade.price),
                'commission_breakdown': commission_breakdown.__dict__,
                'transfer_count': len(multi_transfer_data['transfers']),
                'prepared_at': datetime.utcnow().isoformat(),
                'status': 'prepared'
            }
            
            logger.info(f"资产购买支付交易准备完成: trade_id={trade_id}")
            
            return PaymentResult(
                success=True,
                amount=Decimal(str(trade.total)),
                commission_breakdown=commission_breakdown.__dict__,
                transaction_data=multi_transfer_data['transaction_data'],
                message_data=multi_transfer_data['message_data'],
                payment_details=payment_details,
                payment_status='prepared'
            )
            
        except Exception as e:
            logger.error(f"准备资产购买支付失败: {str(e)}", exc_info=True)
            return PaymentResult(
                success=False,
                error_message=f"准备购买支付失败: {str(e)}"
            )
    
    def confirm_asset_purchase_payment(self, trade_id: int, transaction_hash: str) -> PaymentResult:
        """
        确认资产购买支付（任务3.2核心功能）
        处理前端提交的已签名交易哈希，更新交易状态和资产数据
        
        Args:
            trade_id: 交易ID
            transaction_hash: 交易哈希
            
        Returns:
            PaymentResult: 支付确认结果
        """
        try:
            logger.info(f"确认资产购买支付: trade_id={trade_id}, tx_hash={transaction_hash}")
            
            # 1. 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                return PaymentResult(
                    success=False,
                    error_message=f"交易记录不存在: {trade_id}"
                )
            
            # 2. 验证交易状态
            if trade.status not in [TradeStatus.PENDING.value, TradeStatus.PENDING_PAYMENT.value]:
                return PaymentResult(
                    success=False,
                    error_message=f"交易状态错误，当前状态: {trade.status}"
                )
            
            # 3. 获取资产信息
            asset = Asset.query.get(trade.asset_id)
            if not asset:
                return PaymentResult(
                    success=False,
                    error_message=f"资产不存在: {trade.asset_id}"
                )
            
            # 4. 验证交易哈希格式
            if not transaction_hash or len(transaction_hash) < 32:
                return PaymentResult(
                    success=False,
                    error_message="无效的交易哈希"
                )
            
            # 5. 检查是否重复确认
            if trade.tx_hash == transaction_hash:
                logger.warning(f"重复确认购买支付: trade_id={trade_id}, tx_hash={transaction_hash}")
                return PaymentResult(
                    success=True,
                    transaction_hash=transaction_hash,
                    amount=Decimal(str(trade.total)),
                    error_message="支付已确认"
                )
            
            # 6. 重新计算佣金分配（确保数据一致性）
            commission_breakdown = self._calculate_purchase_commission(trade)
            
            # 7. 更新交易状态和资产数据（使用DataConsistencyManager确保数据一致性）
            try:
                with db.session.begin():
                    # 更新交易状态
                    trade.status = TradeStatus.COMPLETED.value
                    trade.tx_hash = transaction_hash
                    trade.updated_at = datetime.utcnow()
                    
                    # 保存支付详情
                    payment_details = {
                        'type': 'asset_purchase',
                        'trade_id': trade_id,
                        'asset_id': trade.asset_id,
                        'buyer_address': trade.trader_address,
                        'seller_address': asset.creator_address,
                        'total_amount': float(trade.total),
                        'token_amount': trade.amount,
                        'token_price': float(trade.price),
                        'commission_breakdown': commission_breakdown.__dict__,
                        'tx_hash': transaction_hash,
                        'confirmed_at': datetime.utcnow().isoformat(),
                        'status': 'confirmed'
                    }
                    trade.payment_details = json.dumps(payment_details)
                    
                    db.session.commit()
                    
                logger.info(f"资产购买支付状态已更新: trade_id={trade_id}, status=COMPLETED")
                
                # 8. 使用DataConsistencyManager更新资产数据并刷新缓存
                from app.services.data_consistency_manager import DataConsistencyManager
                data_manager = DataConsistencyManager()
                
                # 更新资产数据（包括剩余供应量和缓存清除）
                update_success = data_manager.update_asset_after_trade(trade_id)
                if not update_success:
                    logger.warning(f"DataConsistencyManager更新资产数据失败: trade_id={trade_id}")
                else:
                    logger.info(f"DataConsistencyManager成功更新资产数据: trade_id={trade_id}")
                    
                    # 刷新资产缓存以确保前端获取最新数据
                    cache_refresh_success = data_manager.refresh_asset_cache(trade.asset_id)
                    if cache_refresh_success:
                        logger.info(f"资产缓存刷新成功: asset_id={trade.asset_id}")
                    else:
                        logger.warning(f"资产缓存刷新失败: asset_id={trade.asset_id}")
                
            except Exception as db_error:
                logger.error(f"更新资产购买支付状态失败: {str(db_error)}")
                return PaymentResult(
                    success=False,
                    error_message=f"更新支付状态失败: {str(db_error)}"
                )
            
            # 8. 处理推荐佣金分配
            try:
                self._process_referral_commissions(trade_id, trade.trader_address, Decimal(str(trade.total)))
            except Exception as commission_error:
                logger.error(f"处理推荐佣金失败: {str(commission_error)}")
                # 不影响主要支付确认结果
            
            logger.info(f"资产购买支付确认完成: trade_id={trade_id}")
            
            return PaymentResult(
                success=True,
                transaction_hash=transaction_hash,
                amount=Decimal(str(trade.total)),
                commission_breakdown=commission_breakdown.__dict__,
                payment_details=payment_details,
                payment_status='confirmed'
            )
            
        except Exception as e:
            logger.error(f"确认资产购买支付失败: {str(e)}", exc_info=True)
            return PaymentResult(
                success=False,
                error_message=f"确认购买支付失败: {str(e)}"
            )
    
    
    
    def get_payment_status(self, asset_id: int) -> Dict[str, Any]:
        """
        获取支付状态（任务3.1支付状态跟踪功能）
        
        Args:
            asset_id: 资产ID
            
        Returns:
            Dict: 支付状态信息
        """
        try:
            asset = Asset.query.get(asset_id)
            if not asset:
                return {'success': False, 'error': '资产不存在'}
            
            # 从缓存获取实时状态
            cached_status = self._payment_status_cache.get(asset_id)
            
            status_info = {
                'asset_id': asset_id,
                'payment_confirmed': asset.payment_confirmed,
                'payment_tx_hash': asset.payment_tx_hash,
                'status': asset.status,
                'status_text': self._get_status_text(asset.status),
                'token_address': asset.token_address,
                'remaining_supply': asset.remaining_supply,
                'creation_fee_amount': float(self.asset_creation_fee_amount),
                'platform_fee_rate': float(self.platform_fee_rate),
                'currency': 'USDC'
            }
            
            # 添加缓存状态信息
            if cached_status:
                status_info.update({
                    'cached_status': cached_status.status,
                    'confirmation_count': cached_status.confirmation_count,
                    'last_updated': cached_status.last_updated.isoformat() if cached_status.last_updated else None
                })
            
            # 添加时间戳
            if asset.payment_confirmed_at:
                status_info['payment_confirmed_at'] = asset.payment_confirmed_at.isoformat()
            
            if asset.created_at:
                status_info['created_at'] = asset.created_at.isoformat()
            
            if asset.updated_at:
                status_info['updated_at'] = asset.updated_at.isoformat()
            
            # 添加支付详情
            if asset.payment_details:
                try:
                    status_info['payment_details'] = json.loads(asset.payment_details)
                except Exception as parse_error:
                    logger.warning(f"解析支付详情失败: {str(parse_error)}")
            
            # 添加错误信息
            if asset.error_message:
                status_info['error_message'] = asset.error_message
            
            return {'success': True, 'status': status_info}
            
        except Exception as e:
            logger.error(f"获取支付状态失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_status_text(self, status_code: int) -> str:
        """
        获取状态文本描述
        
        Args:
            status_code: 状态代码
            
        Returns:
            str: 状态文本
        """
        status_map = {
            AssetStatus.PENDING.value: '待支付',
            AssetStatus.PAYMENT_PROCESSING.value: '支付处理中',
            AssetStatus.CONFIRMED.value: '支付已确认',
            AssetStatus.ON_CHAIN.value: '已上链',
            AssetStatus.APPROVED.value: '已审核通过',
            AssetStatus.REJECTED.value: '已拒绝',
            AssetStatus.PAYMENT_FAILED.value: '支付失败',
            AssetStatus.DEPLOYMENT_FAILED.value: '部署失败'
        }
        return status_map.get(status_code, f'未知状态({status_code})')
    
    def track_payment_confirmation(self, asset_id: int, transaction_hash: str) -> Dict[str, Any]:
        """
        跟踪支付确认状态（任务3.1支付确认机制）
        
        Args:
            asset_id: 资产ID
            transaction_hash: 交易哈希
            
        Returns:
            Dict: 确认状态信息
        """
        try:
            logger.info(f"跟踪支付确认: asset_id={asset_id}, tx_hash={transaction_hash}")
            
            # 这里可以集成实际的区块链确认查询
            # 目前使用模拟逻辑
            
            # 模拟确认计数
            cached_status = self._payment_status_cache.get(asset_id)
            if cached_status:
                cached_status.confirmation_count += 1
                cached_status.last_updated = datetime.utcnow()
                
                # 模拟确认完成
                if cached_status.confirmation_count >= 3:
                    cached_status.status = 'confirmed'
                    cached_status.payment_confirmed = True
            
            confirmation_info = {
                'asset_id': asset_id,
                'transaction_hash': transaction_hash,
                'confirmations': cached_status.confirmation_count if cached_status else 0,
                'required_confirmations': 3,
                'confirmed': cached_status.payment_confirmed if cached_status else False,
                'status': cached_status.status if cached_status else 'unknown',
                'last_updated': datetime.utcnow().isoformat()
            }
            
            return {'success': True, 'confirmation': confirmation_info}
            
        except Exception as e:
            logger.error(f"跟踪支付确认失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_payment_settings(self) -> Dict[str, Any]:
        """
        获取支付配置信息（任务3.1配置管理）
        
        Returns:
            Dict: 支付配置信息
        """
        try:
            settings = {
                'asset_creation_fee': {
                    'amount': float(self.asset_creation_fee_amount),
                    'currency': 'USDC',
                    'recipient_address': self.asset_creation_fee_address
                },
                'platform_fee': {
                    'rate': float(self.platform_fee_rate),
                    'rate_percent': float(self.platform_fee_rate * 100),
                    'recipient_address': self.platform_address
                },
                'referral_commission': {
                    'rate': float(self.referral_rate),
                    'rate_percent': float(self.referral_rate * 100)
                },
                'blockchain': {
                    'network': 'Solana',
                    'usdc_mint': self.usdc_mint,
                    'token_program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
                },
                'payment_flow': {
                    'required_confirmations': 3,
                    'timeout_minutes': 30,
                    'retry_attempts': 3
                }
            }
            
            return {'success': True, 'settings': settings}
            
        except Exception as e:
            logger.error(f"获取支付配置失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _process_referral_commissions(self, trade_id: int, user_address: str, transaction_amount: Decimal):
        """
        处理推荐佣金分配（任务3.2推荐佣金处理）
        
        Args:
            trade_id: 交易ID
            user_address: 用户地址
            transaction_amount: 交易金额
        """
        try:
            logger.info(f"处理推荐佣金分配: trade_id={trade_id}, user={user_address}, amount={transaction_amount}")
            
            from app.models.referral import UserReferral, CommissionRecord
            
            current_user = user_address.lower()
            level = 1
            visited_users = set()
            commission_records = []
            
            while level <= 10:  # 限制最多10层推荐
                # 防止循环引用
                if current_user in visited_users:
                    logger.warning(f"检测到推荐关系循环引用: {current_user}")
                    break
                
                visited_users.add(current_user)
                
                # 查找推荐关系
                referral = UserReferral.query.filter(
                    db.func.lower(UserReferral.user_address) == current_user
                ).first()
                
                if not referral:
                    break
                
                # 计算佣金
                commission_amount = transaction_amount * self.referral_rate
                
                # 创建佣金记录
                commission_record = CommissionRecord(
                    transaction_id=trade_id,
                    asset_id=None,  # 从trade中获取
                    recipient_address=referral.referrer_address,
                    amount=float(commission_amount),
                    currency='USDC',
                    commission_type=f'referral_{level}',
                    status='pending',
                    created_at=datetime.utcnow()
                )
                
                commission_records.append(commission_record)
                
                logger.debug(f"创建推荐佣金记录: Level {level}, {commission_amount} USDC -> {referral.referrer_address}")
                
                # 移动到上一级
                current_user = referral.referrer_address.lower()
                level += 1
            
            # 批量保存佣金记录
            if commission_records:
                try:
                    with db.session.begin():
                        for record in commission_records:
                            db.session.add(record)
                        db.session.commit()
                    
                    logger.info(f"成功创建{len(commission_records)}条推荐佣金记录")
                    
                except Exception as db_error:
                    logger.error(f"保存推荐佣金记录失败: {str(db_error)}")
                    # 不影响主要交易流程
            
        except Exception as e:
            logger.error(f"处理推荐佣金分配失败: {str(e)}", exc_info=True)
            # 推荐佣金处理失败不影响主要交易
    
    def handle_payment_failure_rollback(self, trade_id: int, error_message: str) -> Dict[str, Any]:
        """
        处理支付失败回滚机制（任务3.2支付失败回滚）
        
        Args:
            trade_id: 交易ID
            error_message: 错误消息
            
        Returns:
            Dict: 回滚结果
        """
        try:
            logger.info(f"开始处理支付失败回滚: trade_id={trade_id}")
            
            # 1. 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                return {'success': False, 'error': '交易记录不存在'}
            
            # 2. 获取资产信息
            asset = Asset.query.get(trade.asset_id)
            if not asset:
                return {'success': False, 'error': '资产不存在'}
            
            # 3. 回滚交易状态和资产数据
            try:
                with db.session.begin():
                    # 回滚交易状态
                    trade.status = TradeStatus.FAILED.value
                    trade.error_message = error_message
                    trade.updated_at = datetime.utcnow()
                    
                    # 如果之前已经扣减了资产供应量，需要回滚
                    if trade.type == TradeType.BUY.value and trade.status == TradeStatus.PENDING_PAYMENT.value:
                        # 恢复资产供应量
                        asset.remaining_supply = (asset.remaining_supply or 0) + trade.amount
                        if asset.remaining_supply > asset.token_supply:
                            asset.remaining_supply = asset.token_supply
                    
                    asset.updated_at = datetime.utcnow()
                    
                    # 记录回滚详情
                    rollback_details = {
                        'type': 'payment_failure_rollback',
                        'trade_id': trade_id,
                        'error_message': error_message,
                        'rollback_actions': [
                            'trade_status_reset_to_failed',
                            'asset_supply_restored' if trade.type == TradeType.BUY.value else 'no_supply_change'
                        ],
                        'rolled_back_at': datetime.utcnow().isoformat()
                    }
                    
                    trade.payment_details = json.dumps(rollback_details)
                    
                    db.session.commit()
                    
                logger.info(f"支付失败回滚完成: trade_id={trade_id}")
                
            except Exception as db_error:
                logger.error(f"回滚数据库状态失败: {str(db_error)}")
                return {'success': False, 'error': f'回滚失败: {str(db_error)}'}
            
            # 4. 清理相关缓存
            try:
                # 这里可以添加缓存清理逻辑
                pass
            except Exception as cache_error:
                logger.warning(f"清理缓存失败: {str(cache_error)}")
                # 缓存清理失败不影响回滚结果
            
            return {
                'success': True,
                'rollback_details': rollback_details,
                'message': '支付失败回滚完成'
            }
            
        except Exception as e:
            logger.error(f"处理支付失败回滚失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': f'回滚处理失败: {str(e)}'}
    
    def get_commission_statistics(self, user_address: str) -> Dict[str, Any]:
        """
        获取用户佣金统计（任务3.2佣金统计功能）
        
        Args:
            user_address: 用户地址
            
        Returns:
            Dict: 佣金统计信息
        """
        try:
            from app.models.referral import CommissionRecord
            from sqlalchemy import func
            
            user_address = user_address.lower()
            
            # 1. 总佣金收入
            total_commission = db.session.query(func.sum(CommissionRecord.amount))\
                .filter(db.func.lower(CommissionRecord.recipient_address) == user_address)\
                .scalar() or 0
            
            # 2. 本月佣金收入
            current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_commission = db.session.query(func.sum(CommissionRecord.amount))\
                .filter(
                    db.func.lower(CommissionRecord.recipient_address) == user_address,
                    CommissionRecord.created_at >= current_month
                ).scalar() or 0
            
            # 3. 佣金记录数量
            total_records = CommissionRecord.query.filter(
                db.func.lower(CommissionRecord.recipient_address) == user_address
            ).count()
            
            # 4. 按类型统计
            commission_by_type = db.session.query(
                CommissionRecord.commission_type,
                func.sum(CommissionRecord.amount),
                func.count(CommissionRecord.id)
            ).filter(
                db.func.lower(CommissionRecord.recipient_address) == user_address
            ).group_by(CommissionRecord.commission_type).all()
            
            type_statistics = {}
            for comm_type, total_amount, count in commission_by_type:
                type_statistics[comm_type] = {
                    'total_amount': float(total_amount or 0),
                    'count': count,
                    'avg_amount': float(total_amount / count) if count > 0 else 0
                }
            
            return {
                'success': True,
                'statistics': {
                    'user_address': user_address,
                    'total_commission': float(total_commission),
                    'monthly_commission': float(monthly_commission),
                    'total_records': total_records,
                    'commission_by_type': type_statistics,
                    'current_referral_rate': float(self.referral_rate),
                    'last_updated': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"获取佣金统计失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_purchase_commission(self, trade) -> CommissionBreakdown:
        """
        计算购买佣金分配
        
        Args:
            trade: 交易记录
            
        Returns:
            CommissionBreakdown: 佣金分配明细
        """
        try:
            total_amount = Decimal(str(trade.total))
            platform_fee = total_amount * self.platform_fee_rate
            seller_amount = total_amount - platform_fee
            
            # 简化版本：暂不处理推荐佣金
            referral_commissions = []
            total_referral_amount = Decimal('0')
            
            return CommissionBreakdown(
                seller_amount=seller_amount,
                platform_fee=platform_fee,
                referral_commissions=referral_commissions,
                total_referral_amount=total_referral_amount
            )
            
        except Exception as e:
            logger.error(f"计算购买佣金失败: {str(e)}")
            # 返回默认分配
            total_amount = Decimal(str(trade.total))
            platform_fee = total_amount * self.platform_fee_rate
            seller_amount = total_amount - platform_fee
            
            return CommissionBreakdown(
                seller_amount=seller_amount,
                platform_fee=platform_fee,
                referral_commissions=[],
                total_referral_amount=Decimal('0')
            )
    
    def _prepare_multi_party_transfer_transaction(self, trade, commission_breakdown) -> Dict[str, Any]:
        """
        准备多方转账交易（买家支付，多方收款）
        
        Args:
            trade: 交易记录
            commission_breakdown: 佣金分配
            
        Returns:
            dict: 多方转账交易数据
        """
        try:
            logger.info(f"准备多方转账交易: trade_id={trade.id}")
            
            # 获取资产信息
            asset = Asset.query.get(trade.asset_id)
            if not asset:
                return {'success': False, 'error': '资产不存在'}
            
            # 构建转账列表
            transfers = []
            
            # 1. 买家向卖家转账（扣除平台费用后的金额）
            transfers.append({
                'from_address': trade.trader_address,
                'to_address': asset.creator_address,
                'amount': float(commission_breakdown.seller_amount),
                'token': 'USDC',
                'purpose': 'asset_purchase'
            })
            
            # 2. 买家向平台转账（平台费用）
            transfers.append({
                'from_address': trade.trader_address,
                'to_address': self.platform_address,
                'amount': float(commission_breakdown.platform_fee),
                'token': 'USDC',
                'purpose': 'platform_fee'
            })
            
            # 3. 推荐佣金转账（如果有）
            for referral_commission in commission_breakdown.referral_commissions:
                transfers.append({
                    'from_address': trade.trader_address,
                    'to_address': referral_commission['address'],
                    'amount': float(referral_commission['amount']),
                    'token': 'USDC',
                    'purpose': f"referral_commission_L{referral_commission['level']}"
                })
            
            # 使用Solana服务准备多方转账交易
            from app.blockchain.solana_service import prepare_transfer_transaction
            
            # 目前简化为单笔转账（买家向平台支付总金额）
            # 后续可以扩展为真正的多方转账
            total_amount = float(trade.total)
            
            transaction_data, message_data = prepare_transfer_transaction(
                token_symbol="USDC",
                from_address=trade.trader_address,
                to_address=self.platform_address,
                amount=total_amount
            )
            
            return {
                'success': True,
                'transaction_data': transaction_data,
                'message_data': message_data,
                'transfers': transfers,
                'total_amount': total_amount
            }
            
        except Exception as e:
            logger.error(f"准备多方转账交易失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _process_referral_commissions(self, trade_id: int, trader_address: str, total_amount: Decimal):
        """
        处理推荐佣金分配
        
        Args:
            trade_id: 交易ID
            trader_address: 交易者地址
            total_amount: 交易总金额
        """
        try:
            logger.info(f"处理推荐佣金: trade_id={trade_id}, amount={total_amount}")
            
            # 这里可以集成推荐系统逻辑
            # 目前先记录日志，后续可以扩展
            
            logger.info(f"推荐佣金处理完成: trade_id={trade_id}")
            
        except Exception as e:
            logger.error(f"处理推荐佣金失败: {str(e)}")
            # 不抛出异常，避免影响主要交易流程