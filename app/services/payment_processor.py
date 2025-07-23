#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
优化的支付处理器 - 处理资产发布和购买的完整支付流程
"""

import logging
import json
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from flask import current_app
from sqlalchemy import text
from app.extensions import db
from app.models import Asset, Trade
from app.models.asset import AssetStatus
from app.models.trade import TradeStatus, TradeType
from app.blockchain.solana_service import execute_transfer_transaction, validate_solana_address
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

@dataclass
class CommissionBreakdown:
    """佣金分配明细"""
    seller_amount: Decimal
    platform_fee: Decimal
    referral_commissions: List[Dict]
    total_referral_amount: Decimal

class PaymentProcessor:
    """优化的支付处理器"""
    
    def __init__(self):
        self.platform_fee_rate = Decimal(str(ConfigManager.get_platform_fee_rate()))
        self.referral_rate = Decimal('0.05')  # 5%推荐佣金
        self.platform_address = ConfigManager.get_platform_fee_address()
        
    def process_asset_publication_payment(self, asset_id: int, payer_address: str, 
                                        payment_amount: Decimal) -> PaymentResult:
        """
        处理资产发布支付
        
        Args:
            asset_id: 资产ID
            payer_address: 支付方地址
            payment_amount: 支付金额
            
        Returns:
            PaymentResult: 支付处理结果
        """
        try:
            logger.info(f"开始处理资产发布支付: asset_id={asset_id}, payer={payer_address}, amount={payment_amount}")
            
            # 1. 验证资产存在
            asset = Asset.query.get(asset_id)
            if not asset:
                return PaymentResult(
                    success=False,
                    error_message=f"资产不存在: {asset_id}"
                )
            
            # 2. 验证支付地址
            if not validate_solana_address(payer_address):
                return PaymentResult(
                    success=False,
                    error_message=f"无效的支付地址: {payer_address}"
                )
            
            # 3. 计算平台抽成
            platform_fee = payment_amount * self.platform_fee_rate
            net_amount = payment_amount - platform_fee
            
            logger.info(f"发布费用分配: 总额={payment_amount}, 平台费={platform_fee}, 净额={net_amount}")
            
            # 4. 执行USDC转账到平台地址
            try:
                tx_hash = execute_transfer_transaction(
                    token_symbol="USDC",
                    from_address=payer_address,
                    to_address=self.platform_address,
                    amount=float(payment_amount)
                )
                
                logger.info(f"资产发布支付交易成功: {tx_hash}")
                
            except Exception as tx_error:
                logger.error(f"资产发布支付交易失败: {str(tx_error)}")
                return PaymentResult(
                    success=False,
                    error_message=f"支付交易失败: {str(tx_error)}"
                )
            
            # 5. 更新资产支付状态
            with db.session.begin():
                asset.payment_tx_hash = tx_hash
                asset.payment_confirmed = True
                asset.payment_confirmed_at = datetime.utcnow()
                asset.status = AssetStatus.CONFIRMED.value
                
                # 保存支付详情
                payment_details = {
                    'type': 'asset_publication',
                    'total_amount': float(payment_amount),
                    'platform_fee': float(platform_fee),
                    'net_amount': float(net_amount),
                    'payer_address': payer_address,
                    'platform_address': self.platform_address,
                    'tx_hash': tx_hash,
                    'confirmed_at': datetime.utcnow().isoformat()
                }
                asset.payment_details = json.dumps(payment_details)
                
                db.session.commit()
                
            # 6. 触发智能合约资产创建
            try:
                from app.blockchain.asset_service import AssetService
                asset_service = AssetService()
                
                # 异步触发智能合约资产创建
                contract_result = asset_service.create_asset_on_chain(asset_id)
                
                if contract_result.get('success'):
                    logger.info(f"智能合约资产创建已触发: asset_id={asset_id}")
                else:
                    logger.warning(f"智能合约资产创建触发失败: {contract_result.get('error')}")
                    
            except Exception as contract_error:
                logger.error(f"触发智能合约资产创建失败: {str(contract_error)}")
                # 不影响支付确认结果
                
            logger.info(f"资产发布支付处理完成: asset_id={asset_id}")
            
            return PaymentResult(
                success=True,
                transaction_hash=tx_hash,
                amount=payment_amount,
                platform_fee=platform_fee,
                payment_details=payment_details
            )
            
        except Exception as e:
            logger.error(f"处理资产发布支付失败: {str(e)}", exc_info=True)
            return PaymentResult(
                success=False,
                error_message=f"支付处理失败: {str(e)}"
            )
    
    def process_asset_purchase_payment(self, trade_id: int) -> PaymentResult:
        """
        处理资产购买支付（包括多方分账）
        
        Args:
            trade_id: 交易ID
            
        Returns:
            PaymentResult: 支付处理结果
        """
        try:
            logger.info(f"开始处理资产购买支付: trade_id={trade_id}")
            
            # 1. 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                return PaymentResult(
                    success=False,
                    error_message=f"交易记录不存在: {trade_id}"
                )
            
            # 2. 获取资产信息
            asset = Asset.query.get(trade.asset_id)
            if not asset:
                return PaymentResult(
                    success=False,
                    error_message=f"资产不存在: {trade.asset_id}"
                )
            
            # 3. 计算佣金分配
            commission_breakdown = self._calculate_purchase_commission(trade)
            
            # 4. 执行多方转账
            payment_results = self._execute_multi_party_transfer(trade, commission_breakdown)
            
            if not payment_results['success']:
                return PaymentResult(
                    success=False,
                    error_message=payment_results['error']
                )
            
            # 5. 更新交易状态和资产数据
            with db.session.begin():
                # 更新交易状态
                trade.status = TradeStatus.COMPLETED.value
                trade.tx_hash = payment_results['main_tx_hash']
                trade.payment_details = json.dumps(payment_results['details'])
                
                # 更新资产剩余供应量
                if trade.type == TradeType.BUY.value:
                    asset.remaining_supply = (asset.remaining_supply or asset.token_supply) - trade.amount
                elif trade.type == TradeType.SELL.value:
                    asset.remaining_supply = (asset.remaining_supply or 0) + trade.amount
                
                # 确保剩余供应量不为负数
                if asset.remaining_supply < 0:
                    asset.remaining_supply = 0
                
                db.session.commit()
                
            logger.info(f"资产购买支付处理完成: trade_id={trade_id}")
            
            return PaymentResult(
                success=True,
                transaction_hash=payment_results['main_tx_hash'],
                amount=Decimal(str(trade.total)),
                commission_breakdown=commission_breakdown.__dict__,
                payment_details=payment_results['details']
            )
            
        except Exception as e:
            logger.error(f"处理资产购买支付失败: {str(e)}", exc_info=True)
            return PaymentResult(
                success=False,
                error_message=f"购买支付处理失败: {str(e)}"
            )
    
    def _calculate_purchase_commission(self, trade: Trade) -> CommissionBreakdown:
        """
        计算购买佣金分配
        
        Args:
            trade: 交易记录
            
        Returns:
            CommissionBreakdown: 佣金分配明细
        """
        total_amount = Decimal(str(trade.total))
        
        # 1. 计算平台基础费用
        platform_fee = total_amount * self.platform_fee_rate
        
        # 2. 计算推荐佣金（从总金额中扣除）
        referral_commissions = []
        total_referral_amount = Decimal('0')
        
        # 查找买方的推荐关系
        try:
            from app.models.referral import UserReferral
            current_user = trade.trader_address
            level = 1
            
            while level <= 10:  # 限制最多10层推荐
                referral = UserReferral.query.filter_by(user_address=current_user).first()
                if not referral:
                    break
                
                # 计算当前层级佣金
                commission_amount = total_amount * self.referral_rate
                referral_commissions.append({
                    'level': level,
                    'referrer_address': referral.referrer_address,
                    'commission_amount': commission_amount,
                    'rate': self.referral_rate
                })
                
                total_referral_amount += commission_amount
                current_user = referral.referrer_address
                level += 1
                
        except Exception as e:
            logger.warning(f"计算推荐佣金时出错: {str(e)}")
        
        # 3. 计算卖方实际收到的金额
        seller_amount = total_amount - platform_fee - total_referral_amount
        
        logger.info(f"佣金分配计算完成: 总额={total_amount}, 卖方={seller_amount}, 平台费={platform_fee}, 推荐佣金={total_referral_amount}")
        
        return CommissionBreakdown(
            seller_amount=seller_amount,
            platform_fee=platform_fee,
            referral_commissions=referral_commissions,
            total_referral_amount=total_referral_amount
        )
    
    def _execute_multi_party_transfer(self, trade: Trade, commission: CommissionBreakdown) -> Dict[str, Any]:
        """
        执行多方转账
        
        Args:
            trade: 交易记录
            commission: 佣金分配
            
        Returns:
            Dict: 转账结果
        """
        try:
            asset = Asset.query.get(trade.asset_id)
            buyer_address = trade.trader_address
            seller_address = asset.creator_address  # 假设创建者是卖方
            
            transfer_results = []
            
            # 1. 买方向卖方转账
            if commission.seller_amount > 0:
                try:
                    seller_tx = execute_transfer_transaction(
                        token_symbol="USDC",
                        from_address=buyer_address,
                        to_address=seller_address,
                        amount=float(commission.seller_amount)
                    )
                    transfer_results.append({
                        'type': 'seller_payment',
                        'from': buyer_address,
                        'to': seller_address,
                        'amount': float(commission.seller_amount),
                        'tx_hash': seller_tx
                    })
                    logger.info(f"卖方转账成功: {seller_tx}")
                except Exception as e:
                    logger.error(f"卖方转账失败: {str(e)}")
                    return {'success': False, 'error': f"卖方转账失败: {str(e)}"}
            
            # 2. 买方向平台转账（平台费）
            if commission.platform_fee > 0:
                try:
                    platform_tx = execute_transfer_transaction(
                        token_symbol="USDC",
                        from_address=buyer_address,
                        to_address=self.platform_address,
                        amount=float(commission.platform_fee)
                    )
                    transfer_results.append({
                        'type': 'platform_fee',
                        'from': buyer_address,
                        'to': self.platform_address,
                        'amount': float(commission.platform_fee),
                        'tx_hash': platform_tx
                    })
                    logger.info(f"平台费转账成功: {platform_tx}")
                except Exception as e:
                    logger.error(f"平台费转账失败: {str(e)}")
                    return {'success': False, 'error': f"平台费转账失败: {str(e)}"}
            
            # 3. 推荐佣金转账
            for referral_info in commission.referral_commissions:
                if referral_info['commission_amount'] > 0:
                    try:
                        referral_tx = execute_transfer_transaction(
                            token_symbol="USDC",
                            from_address=buyer_address,
                            to_address=referral_info['referrer_address'],
                            amount=float(referral_info['commission_amount'])
                        )
                        transfer_results.append({
                            'type': 'referral_commission',
                            'level': referral_info['level'],
                            'from': buyer_address,
                            'to': referral_info['referrer_address'],
                            'amount': float(referral_info['commission_amount']),
                            'tx_hash': referral_tx
                        })
                        logger.info(f"推荐佣金转账成功 (Level {referral_info['level']}): {referral_tx}")
                    except Exception as e:
                        logger.warning(f"推荐佣金转账失败 (Level {referral_info['level']}): {str(e)}")
                        # 推荐佣金转账失败不影响主交易
            
            # 主交易哈希使用卖方转账的哈希
            main_tx_hash = transfer_results[0]['tx_hash'] if transfer_results else None
            
            return {
                'success': True,
                'main_tx_hash': main_tx_hash,
                'details': {
                    'transfers': transfer_results,
                    'commission_breakdown': commission.__dict__,
                    'processed_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"多方转账执行失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': f"多方转账失败: {str(e)}"}
    
    def get_payment_status(self, asset_id: int) -> Dict[str, Any]:
        """
        获取支付状态
        
        Args:
            asset_id: 资产ID
            
        Returns:
            Dict: 支付状态信息
        """
        try:
            asset = Asset.query.get(asset_id)
            if not asset:
                return {'success': False, 'error': '资产不存在'}
            
            status_info = {
                'asset_id': asset_id,
                'payment_confirmed': asset.payment_confirmed,
                'payment_tx_hash': asset.payment_tx_hash,
                'status': asset.status,
                'token_address': asset.token_address,
                'remaining_supply': asset.remaining_supply
            }
            
            # 添加时间戳
            if asset.payment_confirmed_at:
                status_info['payment_confirmed_at'] = asset.payment_confirmed_at.isoformat()
            
            # 添加支付详情
            if asset.payment_details:
                try:
                    status_info['payment_details'] = json.loads(asset.payment_details)
                except:
                    pass
            
            return {'success': True, 'status': status_info}
            
        except Exception as e:
            logger.error(f"获取支付状态失败: {str(e)}")
            return {'success': False, 'error': str(e)}