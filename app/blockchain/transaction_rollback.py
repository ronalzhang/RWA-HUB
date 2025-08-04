#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
交易回滚机制 - 处理失败交易的回滚和状态恢复
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from app.extensions import db
from app.models.trade import Trade
from app.models.asset import Asset
from app.models.user import User
from app.blockchain.transaction_manager import TransactionStatus, TransactionResult

logger = logging.getLogger(__name__)

class RollbackReason(Enum):
    """回滚原因枚举"""
    TRANSACTION_FAILED = "transaction_failed"
    TIMEOUT = "timeout"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    USER_CANCELLED = "user_cancelled"
    SYSTEM_ERROR = "system_error"

@dataclass
class RollbackAction:
    """回滚动作"""
    action_type: str
    target_table: str
    target_id: int
    original_data: Dict[str, Any]
    rollback_data: Dict[str, Any]
    executed: bool = False
    error: Optional[str] = None

@dataclass
class RollbackPlan:
    """回滚计划"""
    transaction_id: str
    reason: RollbackReason
    actions: List[RollbackAction]
    created_at: datetime
    executed_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None

class TransactionRollbackManager:
    """交易回滚管理器"""
    
    def __init__(self):
        self.rollback_plans = {}  # 存储回滚计划
        
    def create_rollback_plan(
        self,
        transaction_id: str,
        trade_id: int,
        reason: RollbackReason
    ) -> RollbackPlan:
        """
        创建回滚计划
        
        Args:
            transaction_id: 交易ID
            trade_id: 交易记录ID
            reason: 回滚原因
            
        Returns:
            RollbackPlan: 回滚计划
        """
        logger.info(f"创建回滚计划: 交易ID={transaction_id}, 交易记录ID={trade_id}, 原因={reason.value}")
        
        try:
            # 获取交易记录
            trade = Trade.query.get(trade_id)
            if not trade:
                raise ValueError(f"交易记录不存在: {trade_id}")
            
            # 获取相关资产
            asset = Asset.query.get(trade.asset_id)
            if not asset:
                raise ValueError(f"资产不存在: {trade.asset_id}")
            
            actions = []
            
            # 1. 回滚交易状态
            actions.append(RollbackAction(
                action_type="update_trade_status",
                target_table="trades",
                target_id=trade_id,
                original_data={
                    "status": trade.status,
                    "tx_hash": trade.tx_hash,
                    "error_message": trade.error_message
                },
                rollback_data={
                    "status": "failed",
                    "tx_hash": None,
                    "error_message": f"交易回滚: {reason.value}"
                }
            ))
            
            # 2. 回滚资产供应量（如果是购买交易）
            if trade.type == 'buy':
                actions.append(RollbackAction(
                    action_type="restore_asset_supply",
                    target_table="assets",
                    target_id=asset.id,
                    original_data={
                        "remaining_supply": asset.remaining_supply
                    },
                    rollback_data={
                        "remaining_supply": asset.remaining_supply + trade.amount
                    }
                ))
            
            # 3. 回滚用户持有量（如果已经更新）
            if hasattr(trade, 'user_holding_updated') and trade.user_holding_updated:
                actions.append(RollbackAction(
                    action_type="rollback_user_holding",
                    target_table="holdings",
                    target_id=trade.id,  # 使用trade_id作为标识
                    original_data={
                        "user_address": trade.trader_address,
                        "asset_id": trade.asset_id,
                        "amount": trade.amount
                    },
                    rollback_data={
                        "action": "subtract_holding"
                    }
                ))
            
            # 4. 回滚佣金记录（如果已经创建）
            if hasattr(trade, 'commission_created') and trade.commission_created:
                actions.append(RollbackAction(
                    action_type="rollback_commission",
                    target_table="commissions",
                    target_id=trade.id,
                    original_data={
                        "trade_id": trade.id
                    },
                    rollback_data={
                        "action": "delete_commission_records"
                    }
                ))
            
            # 创建回滚计划
            rollback_plan = RollbackPlan(
                transaction_id=transaction_id,
                reason=reason,
                actions=actions,
                created_at=datetime.utcnow()
            )
            
            # 存储回滚计划
            self.rollback_plans[transaction_id] = rollback_plan
            
            logger.info(f"回滚计划创建完成，包含 {len(actions)} 个动作")
            return rollback_plan
            
        except Exception as e:
            logger.error(f"创建回滚计划失败: {e}")
            raise
    
    def execute_rollback(self, transaction_id: str) -> bool:
        """
        执行回滚
        
        Args:
            transaction_id: 交易ID
            
        Returns:
            bool: 回滚是否成功
        """
        logger.info(f"开始执行回滚: {transaction_id}")
        
        if transaction_id not in self.rollback_plans:
            logger.error(f"回滚计划不存在: {transaction_id}")
            return False
        
        rollback_plan = self.rollback_plans[transaction_id]
        
        try:
            with db.session.begin():
                success_count = 0
                
                for action in rollback_plan.actions:
                    try:
                        self._execute_rollback_action(action)
                        action.executed = True
                        success_count += 1
                        logger.debug(f"回滚动作执行成功: {action.action_type}")
                        
                    except Exception as e:
                        action.error = str(e)
                        logger.error(f"回滚动作执行失败: {action.action_type}, 错误: {e}")
                        # 继续执行其他动作，不要因为一个动作失败就停止整个回滚
                
                # 更新回滚计划状态
                rollback_plan.executed_at = datetime.utcnow()
                rollback_plan.success = success_count == len(rollback_plan.actions)
                
                if rollback_plan.success:
                    logger.info(f"回滚执行成功: {transaction_id}")
                else:
                    logger.warning(f"回滚部分成功: {transaction_id}, 成功: {success_count}/{len(rollback_plan.actions)}")
                
                return rollback_plan.success
                
        except Exception as e:
            rollback_plan.error = str(e)
            logger.error(f"回滚执行失败: {transaction_id}, 错误: {e}")
            return False
    
    def _execute_rollback_action(self, action: RollbackAction):
        """执行单个回滚动作"""
        if action.action_type == "update_trade_status":
            self._rollback_trade_status(action)
        elif action.action_type == "restore_asset_supply":
            self._rollback_asset_supply(action)
        elif action.action_type == "rollback_user_holding":
            self._rollback_user_holding(action)
        elif action.action_type == "rollback_commission":
            self._rollback_commission(action)
        else:
            raise ValueError(f"未知的回滚动作类型: {action.action_type}")
    
    def _rollback_trade_status(self, action: RollbackAction):
        """回滚交易状态"""
        trade = Trade.query.get(action.target_id)
        if not trade:
            raise ValueError(f"交易记录不存在: {action.target_id}")
        
        # 更新交易状态
        for key, value in action.rollback_data.items():
            setattr(trade, key, value)
        
        # 添加回滚时间戳
        trade.updated_at = datetime.utcnow()
        
        db.session.add(trade)
        logger.debug(f"交易状态已回滚: {action.target_id}")
    
    def _rollback_asset_supply(self, action: RollbackAction):
        """回滚资产供应量"""
        asset = Asset.query.get(action.target_id)
        if not asset:
            raise ValueError(f"资产不存在: {action.target_id}")
        
        # 恢复供应量
        asset.remaining_supply = action.rollback_data["remaining_supply"]
        asset.updated_at = datetime.utcnow()
        
        db.session.add(asset)
        logger.debug(f"资产供应量已回滚: {action.target_id}")
    
    def _rollback_user_holding(self, action: RollbackAction):
        """回滚用户持有量"""
        from app.models.holding import Holding
        
        user_address = action.original_data["user_address"]
        asset_id = action.original_data["asset_id"]
        amount = action.original_data["amount"]
        
        # 查找用户持有记录
        holding = Holding.query.filter_by(
            user_address=user_address,
            asset_id=asset_id
        ).first()
        
        if holding:
            # 减少持有量
            holding.amount -= amount
            
            # 如果持有量为0或负数，删除记录
            if holding.amount <= 0:
                db.session.delete(holding)
                logger.debug(f"用户持有记录已删除: {user_address}, 资产: {asset_id}")
            else:
                holding.updated_at = datetime.utcnow()
                db.session.add(holding)
                logger.debug(f"用户持有量已回滚: {user_address}, 资产: {asset_id}, 数量: -{amount}")
    
    def _rollback_commission(self, action: RollbackAction):
        """回滚佣金记录"""
        from app.models.commission import CommissionRecord
        
        trade_id = action.original_data["trade_id"]
        
        # 删除相关的佣金记录
        commission_records = CommissionRecord.query.filter_by(trade_id=trade_id).all()
        
        for record in commission_records:
            db.session.delete(record)
        
        logger.debug(f"佣金记录已回滚: 交易ID {trade_id}, 删除 {len(commission_records)} 条记录")
    
    def auto_rollback_failed_transactions(self, max_age_minutes: int = 30):
        """
        自动回滚失败的交易
        
        Args:
            max_age_minutes: 最大年龄（分钟）
        """
        logger.info(f"开始自动回滚失败交易，最大年龄: {max_age_minutes}分钟")
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        # 查找需要回滚的交易
        failed_trades = Trade.query.filter(
            Trade.status.in_(['pending', 'processing']),
            Trade.created_at < cutoff_time,
            Trade.tx_hash.isnot(None)  # 已经有交易哈希但状态异常
        ).all()
        
        rollback_count = 0
        
        for trade in failed_trades:
            try:
                # 创建并执行回滚计划
                rollback_plan = self.create_rollback_plan(
                    transaction_id=f"auto_rollback_{trade.id}",
                    trade_id=trade.id,
                    reason=RollbackReason.TIMEOUT
                )
                
                if self.execute_rollback(rollback_plan.transaction_id):
                    rollback_count += 1
                    logger.info(f"自动回滚成功: 交易ID {trade.id}")
                else:
                    logger.warning(f"自动回滚失败: 交易ID {trade.id}")
                    
            except Exception as e:
                logger.error(f"自动回滚交易 {trade.id} 时出错: {e}")
        
        logger.info(f"自动回滚完成，成功回滚 {rollback_count} 个交易")
        return rollback_count
    
    def get_rollback_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取回滚历史"""
        history = []
        
        for transaction_id, plan in list(self.rollback_plans.items())[-limit:]:
            history.append({
                'transaction_id': transaction_id,
                'reason': plan.reason.value,
                'actions_count': len(plan.actions),
                'success': plan.success,
                'created_at': plan.created_at.isoformat(),
                'executed_at': plan.executed_at.isoformat() if plan.executed_at else None,
                'error': plan.error
            })
        
        return history
    
    def cleanup_old_rollback_plans(self, max_age_days: int = 7):
        """清理旧的回滚计划"""
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        
        to_remove = []
        for transaction_id, plan in self.rollback_plans.items():
            if plan.created_at < cutoff_time:
                to_remove.append(transaction_id)
        
        for transaction_id in to_remove:
            del self.rollback_plans[transaction_id]
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个旧回滚计划")

# 全局回滚管理器实例
rollback_manager = TransactionRollbackManager()