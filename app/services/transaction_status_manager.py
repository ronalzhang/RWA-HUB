#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
交易状态管理器 - 实现任务3.3优化交易状态管理
处理交易状态流转、实时更新和历史记录
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from flask import current_app
from sqlalchemy import text, and_, or_
from app.extensions import db
from app.models import Trade, Asset
from app.models.trade import TradeStatus, TradeType
from app.models.asset import AssetStatus

logger = logging.getLogger(__name__)

class TransactionStatusFlow(Enum):
    """交易状态流转枚举"""
    PENDING = 'pending'                    # 待处理
    PENDING_PAYMENT = 'pending_payment'    # 等待支付
    PENDING_CONFIRMATION = 'pending_confirmation'  # 等待链上确认
    PROCESSING = 'processing'              # 处理中
    COMPLETED = 'completed'                # 已完成
    FAILED = 'failed'                      # 失败
    CANCELLED = 'cancelled'                # 已取消
    EXPIRED = 'expired'                    # 已过期

@dataclass
class TransactionStatusInfo:
    """交易状态信息"""
    trade_id: int
    current_status: str
    previous_status: Optional[str]
    status_updated_at: datetime
    confirmation_count: int = 0
    estimated_completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    status_history: List[Dict] = None

class TransactionStatusManager:
    """交易状态管理器 - 实现任务3.3核心功能"""
    
    def __init__(self):
        self.status_cache = {}
        self.confirmation_requirements = {
            'solana': 3,  # Solana需要3个确认
            'ethereum': 12  # 以太坊需要12个确认
        }
        self.transaction_timeout = timedelta(minutes=30)  # 30分钟超时
        
        logger.info("TransactionStatusManager初始化完成")
    
    def update_transaction_status(self, trade_id: int, new_status: str, 
                                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        更新交易状态（任务3.3核心功能）
        
        Args:
            trade_id: 交易ID
            new_status: 新状态
            context: 状态更新上下文信息
            
        Returns:
            Dict: 状态更新结果
        """
        try:
            logger.info(f"更新交易状态: trade_id={trade_id}, new_status={new_status}")
            
            # 1. 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                return {'success': False, 'error': f'交易记录不存在: {trade_id}'}
            
            # 2. 验证状态转换的合法性
            validation_result = self._validate_status_transition(
                trade.status, new_status, context
            )
            if not validation_result['valid']:
                return {
                    'success': False, 
                    'error': f'状态转换不合法: {validation_result["reason"]}'
                }
            
            # 3. 记录状态变更历史
            old_status = trade.status
            status_change_record = {
                'from_status': old_status,
                'to_status': new_status,
                'changed_at': datetime.utcnow().isoformat(),
                'context': context or {},
                'change_reason': context.get('reason', 'Manual update') if context else 'Manual update'
            }
            
            # 4. 更新交易状态
            try:
                with db.session.begin():
                    trade.status = new_status
                    trade.updated_at = datetime.utcnow()
                    
                    # 更新错误信息
                    if new_status == TradeStatus.FAILED.value and context:
                        trade.error_message = context.get('error_message')
                    
                    # 更新交易哈希
                    if context and context.get('tx_hash'):
                        trade.tx_hash = context['tx_hash']
                    
                    # 保存状态历史
                    existing_history = []
                    if trade.payment_details:
                        try:
                            payment_data = json.loads(trade.payment_details)
                            existing_history = payment_data.get('status_history', [])
                        except:
                            pass
                    
                    existing_history.append(status_change_record)
                    
                    payment_details = {
                        'status_history': existing_history,
                        'current_status': new_status,
                        'last_updated': datetime.utcnow().isoformat()
                    }
                    
                    # 合并现有支付详情
                    if trade.payment_details:
                        try:
                            existing_details = json.loads(trade.payment_details)
                            payment_details.update(existing_details)
                        except:
                            pass
                    
                    trade.payment_details = json.dumps(payment_details)
                    
                    db.session.commit()
                    
                logger.info(f"交易状态更新成功: trade_id={trade_id}, {old_status} -> {new_status}")
                
            except Exception as db_error:
                logger.error(f"更新交易状态失败: {str(db_error)}")
                return {'success': False, 'error': f'数据库更新失败: {str(db_error)}'}
            
            # 5. 处理状态变更的副作用（包括自动数据更新）
            try:
                self._handle_status_change_side_effects(trade_id, old_status, new_status, context)
                
                # 如果交易完成，自动更新资产数据
                if new_status == TradeStatus.COMPLETED.value:
                    self._trigger_automatic_data_update(trade_id)
                    
            except Exception as side_effect_error:
                logger.error(f"处理状态变更副作用失败: {str(side_effect_error)}")
                # 不影响主要状态更新
            
            # 6. 更新缓存
            status_info = TransactionStatusInfo(
                trade_id=trade_id,
                current_status=new_status,
                previous_status=old_status,
                status_updated_at=datetime.utcnow(),
                confirmation_count=context.get('confirmation_count', 0) if context else 0,
                blockchain_tx_hash=context.get('tx_hash') if context else None,
                status_history=existing_history
            )
            self.status_cache[trade_id] = status_info
            
            return {
                'success': True,
                'status_change': status_change_record,
                'current_status': new_status,
                'previous_status': old_status
            }
            
        except Exception as e:
            logger.error(f"更新交易状态失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': f'状态更新失败: {str(e)}'}
    
    def get_real_time_transaction_status(self, trade_id: int) -> Dict[str, Any]:
        """
        获取实时交易状态（任务3.3实时状态更新）
        
        Args:
            trade_id: 交易ID
            
        Returns:
            Dict: 实时状态信息
        """
        try:
            logger.debug(f"获取实时交易状态: trade_id={trade_id}")
            
            # 1. 从缓存获取状态信息
            cached_status = self.status_cache.get(trade_id)
            
            # 2. 从数据库获取最新状态
            trade = Trade.query.get(trade_id)
            if not trade:
                return {'success': False, 'error': '交易记录不存在'}
            
            # 3. 获取资产信息
            asset = None
            if trade.asset_id:
                asset = Asset.query.get(trade.asset_id)
            
            # 4. 构建状态信息
            status_info = {
                'trade_id': trade_id,
                'current_status': trade.status,
                'status_text': self._get_status_text(trade.status),
                'created_at': trade.created_at.isoformat() if trade.created_at else None,
                'updated_at': trade.updated_at.isoformat() if trade.updated_at else None,
                'tx_hash': trade.tx_hash,
                'error_message': trade.error_message,
                'trade_details': {
                    'type': trade.type,
                    'amount': trade.amount,
                    'price': float(trade.price),
                    'total': float(trade.total) if trade.total else None,
                    'trader_address': trade.trader_address
                }
            }
            
            # 5. 添加资产信息
            if asset:
                status_info['asset_info'] = {
                    'id': asset.id,
                    'name': asset.name,
                    'token_symbol': asset.token_symbol,
                    'remaining_supply': asset.remaining_supply
                }
            
            # 6. 添加缓存状态信息
            if cached_status:
                status_info.update({
                    'confirmation_count': cached_status.confirmation_count,
                    'estimated_completion_time': cached_status.estimated_completion_time.isoformat() if cached_status.estimated_completion_time else None,
                    'cache_updated_at': cached_status.status_updated_at.isoformat()
                })
            
            # 7. 添加状态历史
            if trade.payment_details:
                try:
                    payment_data = json.loads(trade.payment_details)
                    status_info['status_history'] = payment_data.get('status_history', [])
                except:
                    status_info['status_history'] = []
            else:
                status_info['status_history'] = []
            
            # 8. 计算预估完成时间
            if trade.status in [TradeStatus.PENDING_PAYMENT.value, TradeStatus.PENDING_CONFIRMATION.value]:
                estimated_time = self._calculate_estimated_completion_time(trade)
                if estimated_time:
                    status_info['estimated_completion_time'] = estimated_time.isoformat()
            
            return {'success': True, 'status': status_info}
            
        except Exception as e:
            logger.error(f"获取实时交易状态失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def track_transaction_confirmation(self, trade_id: int, tx_hash: str) -> Dict[str, Any]:
        """
        跟踪交易确认状态（任务3.3交易确认处理）
        
        Args:
            trade_id: 交易ID
            tx_hash: 交易哈希
            
        Returns:
            Dict: 确认状态信息
        """
        try:
            logger.info(f"跟踪交易确认: trade_id={trade_id}, tx_hash={tx_hash}")
            
            # 1. 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                return {'success': False, 'error': '交易记录不存在'}
            
            # 2. 模拟区块链确认查询（实际环境中应该调用区块链API）
            confirmation_info = self._query_blockchain_confirmation(tx_hash)
            
            # 3. 更新确认状态
            cached_status = self.status_cache.get(trade_id)
            if cached_status:
                cached_status.confirmation_count = confirmation_info['confirmations']
                cached_status.status_updated_at = datetime.utcnow()
                cached_status.blockchain_tx_hash = tx_hash
            
            # 4. 检查是否达到确认要求
            required_confirmations = self.confirmation_requirements.get('solana', 3)
            is_confirmed = confirmation_info['confirmations'] >= required_confirmations
            
            # 5. 如果确认完成，更新交易状态
            if is_confirmed and trade.status == TradeStatus.PENDING_CONFIRMATION.value:
                self.update_transaction_status(
                    trade_id, 
                    TradeStatus.COMPLETED.value,
                    {
                        'reason': 'Blockchain confirmation completed',
                        'confirmation_count': confirmation_info['confirmations'],
                        'tx_hash': tx_hash
                    }
                )
            
            confirmation_result = {
                'trade_id': trade_id,
                'tx_hash': tx_hash,
                'confirmations': confirmation_info['confirmations'],
                'required_confirmations': required_confirmations,
                'is_confirmed': is_confirmed,
                'confirmation_status': 'confirmed' if is_confirmed else 'pending',
                'last_checked': datetime.utcnow().isoformat()
            }
            
            return {'success': True, 'confirmation': confirmation_result}
            
        except Exception as e:
            logger.error(f"跟踪交易确认失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_transaction_history(self, trade_id: int) -> Dict[str, Any]:
        """
        获取交易历史记录（任务3.3交易历史记录功能）
        
        Args:
            trade_id: 交易ID
            
        Returns:
            Dict: 交易历史记录
        """
        try:
            logger.debug(f"获取交易历史记录: trade_id={trade_id}")
            
            # 1. 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                return {'success': False, 'error': '交易记录不存在'}
            
            # 2. 解析状态历史
            status_history = []
            if trade.payment_details:
                try:
                    payment_data = json.loads(trade.payment_details)
                    status_history = payment_data.get('status_history', [])
                except:
                    pass
            
            # 3. 如果没有历史记录，创建基础记录
            if not status_history:
                status_history = [{
                    'from_status': None,
                    'to_status': trade.status,
                    'changed_at': trade.created_at.isoformat() if trade.created_at else datetime.utcnow().isoformat(),
                    'context': {},
                    'change_reason': 'Transaction created'
                }]
            
            # 4. 构建完整历史信息
            history_info = {
                'trade_id': trade_id,
                'current_status': trade.status,
                'total_status_changes': len(status_history),
                'status_history': status_history,
                'trade_created_at': trade.created_at.isoformat() if trade.created_at else None,
                'last_updated_at': trade.updated_at.isoformat() if trade.updated_at else None,
                'total_duration': self._calculate_transaction_duration(trade),
                'tx_hash': trade.tx_hash
            }
            
            # 5. 添加状态统计
            status_stats = {}
            for record in status_history:
                status = record['to_status']
                if status not in status_stats:
                    status_stats[status] = {
                        'count': 0,
                        'first_time': record['changed_at'],
                        'last_time': record['changed_at']
                    }
                status_stats[status]['count'] += 1
                status_stats[status]['last_time'] = record['changed_at']
            
            history_info['status_statistics'] = status_stats
            
            return {'success': True, 'history': history_info}
            
        except Exception as e:
            logger.error(f"获取交易历史记录失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_transaction_timeout(self) -> Dict[str, Any]:
        """
        处理交易超时（任务3.3交易超时处理）
        
        Returns:
            Dict: 超时处理结果
        """
        try:
            logger.info("开始处理交易超时检查")
            
            # 1. 查找超时的交易
            timeout_threshold = datetime.utcnow() - self.transaction_timeout
            
            timeout_trades = Trade.query.filter(
                and_(
                    Trade.status.in_([
                        TradeStatus.PENDING_PAYMENT.value,
                        TradeStatus.PENDING_CONFIRMATION.value
                    ]),
                    Trade.updated_at < timeout_threshold
                )
            ).all()
            
            logger.info(f"发现{len(timeout_trades)}个超时交易")
            
            # 2. 处理每个超时交易
            processed_count = 0
            failed_count = 0
            
            for trade in timeout_trades:
                try:
                    # 更新为超时状态
                    result = self.update_transaction_status(
                        trade.id,
                        TransactionStatusFlow.EXPIRED.value,
                        {
                            'reason': 'Transaction timeout',
                            'timeout_threshold': timeout_threshold.isoformat(),
                            'error_message': f'交易超时，超过{self.transaction_timeout.total_seconds()/60}分钟未完成'
                        }
                    )
                    
                    if result['success']:
                        processed_count += 1
                        logger.info(f"交易超时处理成功: trade_id={trade.id}")
                    else:
                        failed_count += 1
                        logger.error(f"交易超时处理失败: trade_id={trade.id}, error={result['error']}")
                        
                except Exception as trade_error:
                    failed_count += 1
                    logger.error(f"处理超时交易失败: trade_id={trade.id}, error={str(trade_error)}")
            
            result = {
                'total_timeout_trades': len(timeout_trades),
                'processed_successfully': processed_count,
                'processing_failed': failed_count,
                'timeout_threshold': timeout_threshold.isoformat(),
                'processed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"交易超时处理完成: {result}")
            
            return {'success': True, 'timeout_processing': result}
            
        except Exception as e:
            logger.error(f"处理交易超时失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _validate_status_transition(self, current_status: str, new_status: str, 
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        验证状态转换的合法性
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            context: 上下文信息
            
        Returns:
            Dict: 验证结果
        """
        # 定义合法的状态转换
        valid_transitions = {
            TradeStatus.PENDING.value: [
                TradeStatus.PENDING_PAYMENT.value,
                TradeStatus.FAILED.value,
                TradeStatus.CANCELLED.value
            ],
            TradeStatus.PENDING_PAYMENT.value: [
                TradeStatus.PENDING_CONFIRMATION.value,
                TradeStatus.PROCESSING.value,
                TradeStatus.FAILED.value,
                TradeStatus.CANCELLED.value,
                TransactionStatusFlow.EXPIRED.value
            ],
            TradeStatus.PENDING_CONFIRMATION.value: [
                TradeStatus.COMPLETED.value,
                TradeStatus.FAILED.value,
                TransactionStatusFlow.EXPIRED.value
            ],
            TradeStatus.PROCESSING.value: [
                TradeStatus.COMPLETED.value,
                TradeStatus.FAILED.value
            ],
            TradeStatus.COMPLETED.value: [],  # 完成状态不能转换
            TradeStatus.FAILED.value: [
                TradeStatus.PENDING.value  # 允许重试
            ],
            TradeStatus.CANCELLED.value: [],  # 取消状态不能转换
            TransactionStatusFlow.EXPIRED.value: [
                TradeStatus.PENDING.value  # 允许重新开始
            ]
        }
        
        allowed_transitions = valid_transitions.get(current_status, [])
        
        if new_status in allowed_transitions:
            return {'valid': True, 'reason': 'Valid transition'}
        else:
            return {
                'valid': False,
                'reason': f'Invalid transition from {current_status} to {new_status}'
            }
    
    def _handle_status_change_side_effects(self, trade_id: int, old_status: str, 
                                         new_status: str, context: Dict[str, Any] = None):
        """
        处理状态变更的副作用
        
        Args:
            trade_id: 交易ID
            old_status: 旧状态
            new_status: 新状态
            context: 上下文信息
        """
        try:
            # 1. 如果交易完成，更新资产供应量
            if new_status == TradeStatus.COMPLETED.value:
                self._update_asset_supply_on_completion(trade_id)
            
            # 2. 如果交易失败，处理回滚
            elif new_status == TradeStatus.FAILED.value:
                self._handle_transaction_failure_rollback(trade_id, context)
            
            # 3. 如果交易超时，清理相关资源
            elif new_status == TransactionStatusFlow.EXPIRED.value:
                self._cleanup_expired_transaction(trade_id)
            
        except Exception as e:
            logger.error(f"处理状态变更副作用失败: {str(e)}")
    
    def _update_asset_supply_on_completion(self, trade_id: int):
        """交易完成时更新资产供应量"""
        try:
            trade = Trade.query.get(trade_id)
            if not trade or not trade.asset_id:
                return
            
            asset = Asset.query.get(trade.asset_id)
            if not asset:
                return
            
            with db.session.begin():
                if trade.type == TradeType.BUY.value:
                    asset.remaining_supply = (asset.remaining_supply or asset.token_supply) - trade.amount
                elif trade.type == TradeType.SELL.value:
                    asset.remaining_supply = (asset.remaining_supply or 0) + trade.amount
                
                # 确保供应量不为负数
                if asset.remaining_supply < 0:
                    asset.remaining_supply = 0
                
                asset.updated_at = datetime.utcnow()
                db.session.commit()
                
            logger.info(f"资产供应量更新完成: asset_id={asset.id}, remaining_supply={asset.remaining_supply}")
            
        except Exception as e:
            logger.error(f"更新资产供应量失败: {str(e)}")
    
    def _handle_transaction_failure_rollback(self, trade_id: int, context: Dict[str, Any] = None):
        """处理交易失败回滚"""
        try:
            # 这里可以调用PaymentProcessor的回滚方法
            from app.services.payment_processor import PaymentProcessor
            
            payment_processor = PaymentProcessor()
            error_message = context.get('error_message', '交易失败') if context else '交易失败'
            
            rollback_result = payment_processor.handle_payment_failure_rollback(trade_id, error_message)
            
            if rollback_result['success']:
                logger.info(f"交易失败回滚完成: trade_id={trade_id}")
            else:
                logger.error(f"交易失败回滚失败: trade_id={trade_id}, error={rollback_result['error']}")
                
        except Exception as e:
            logger.error(f"处理交易失败回滚失败: {str(e)}")
    
    def _trigger_automatic_data_update(self, trade_id: int):
        """
        触发自动数据更新（任务5.2核心功能）
        当交易完成时自动更新相关数据并清除缓存
        
        Args:
            trade_id: 交易ID
        """
        try:
            logger.info(f"触发自动数据更新: trade_id={trade_id}")
            
            # 1. 使用DataConsistencyManager更新资产数据
            from app.services.data_consistency_manager import DataConsistencyManager
            data_manager = DataConsistencyManager()
            
            # 2. 更新资产数据（包括剩余供应量和缓存清除）
            update_success = data_manager.update_asset_after_trade(trade_id)
            
            if update_success:
                logger.info(f"自动数据更新成功: trade_id={trade_id}")
                
                # 3. 获取交易信息以清除相关缓存
                trade = Trade.query.get(trade_id)
                if trade and trade.asset_id:
                    # 清除资产相关的所有缓存
                    data_manager._invalidate_cache(f"asset_data:{trade.asset_id}")
                    
                    # 如果有Redis，还可以清除其他相关缓存
                    if data_manager._redis_client:
                        try:
                            # 清除交易历史缓存
                            pattern = f"trade_history:{trade.asset_id}:*"
                            keys = data_manager._redis_client.keys(pattern)
                            if keys:
                                data_manager._redis_client.delete(*keys)
                                logger.info(f"已清除交易历史缓存: {len(keys)} 个key")
                        except Exception as cache_error:
                            logger.warning(f"清除交易历史缓存失败: {str(cache_error)}")
                    
                    logger.info(f"已清除资产相关缓存: asset_id={trade.asset_id}")
                    
            else:
                logger.error(f"自动数据更新失败: trade_id={trade_id}")
                
        except Exception as e:
            logger.error(f"触发自动数据更新失败: {str(e)}", exc_info=True)
    
    def _cleanup_expired_transaction(self, trade_id: int):
        """清理过期交易"""
        try:
            # 清理缓存
            if trade_id in self.status_cache:
                del self.status_cache[trade_id]
            
            logger.info(f"过期交易清理完成: trade_id={trade_id}")
            
        except Exception as e:
            logger.error(f"清理过期交易失败: {str(e)}")
    
    def _query_blockchain_confirmation(self, tx_hash: str) -> Dict[str, Any]:
        """查询区块链确认状态（模拟）"""
        # 在实际环境中，这里应该调用Solana RPC API
        # 现在返回模拟数据
        import random
        
        return {
            'tx_hash': tx_hash,
            'confirmations': random.randint(0, 5),
            'block_height': random.randint(100000, 200000),
            'confirmed': random.choice([True, False])
        }
    
    def _calculate_estimated_completion_time(self, trade: Trade) -> Optional[datetime]:
        """计算预估完成时间"""
        try:
            if trade.status == TradeStatus.PENDING_PAYMENT.value:
                # 支付通常在10分钟内完成
                return datetime.utcnow() + timedelta(minutes=10)
            elif trade.status == TradeStatus.PENDING_CONFIRMATION.value:
                # 确认通常在5分钟内完成
                return datetime.utcnow() + timedelta(minutes=5)
            else:
                return None
                
        except Exception as e:
            logger.error(f"计算预估完成时间失败: {str(e)}")
            return None
    
    def _calculate_transaction_duration(self, trade: Trade) -> Optional[str]:
        """计算交易持续时间"""
        try:
            if not trade.created_at:
                return None
            
            end_time = trade.updated_at or datetime.utcnow()
            duration = end_time - trade.created_at
            
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}小时{minutes}分钟{seconds}秒"
            elif minutes > 0:
                return f"{minutes}分钟{seconds}秒"
            else:
                return f"{seconds}秒"
                
        except Exception as e:
            logger.error(f"计算交易持续时间失败: {str(e)}")
            return None
    
    def _get_status_text(self, status_code: str) -> str:
        """获取状态文本描述"""
        status_map = {
            TradeStatus.PENDING.value: '待处理',
            TradeStatus.PENDING_PAYMENT.value: '等待支付',
            TradeStatus.PENDING_CONFIRMATION.value: '等待确认',
            TradeStatus.PROCESSING.value: '处理中',
            TradeStatus.COMPLETED.value: '已完成',
            TradeStatus.FAILED.value: '失败',
            TradeStatus.CANCELLED.value: '已取消',
            TransactionStatusFlow.EXPIRED.value: '已过期'
        }
        return status_map.get(status_code, f'未知状态({status_code})')