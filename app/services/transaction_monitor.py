#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
交易监控服务 - 实时跟踪和监控Solana交易状态
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from app.blockchain.solana_service import (
    get_solana_connection, check_transaction_status, 
    get_network_health_report, connection_manager
)
from app.blockchain.transaction_manager import TransactionStatus
from app.blockchain.transaction_rollback import rollback_manager, RollbackReason
from app.extensions import db
from app.models.trade import Trade

logger = logging.getLogger(__name__)

class MonitoringLevel(Enum):
    """监控级别"""
    BASIC = "basic"      # 基础监控
    DETAILED = "detailed"  # 详细监控
    INTENSIVE = "intensive"  # 密集监控

@dataclass
class TransactionMonitorConfig:
    """交易监控配置"""
    check_interval: float = 5.0  # 检查间隔（秒）
    timeout_threshold: int = 300  # 超时阈值（秒）
    max_retries: int = 5  # 最大重试次数
    monitoring_level: MonitoringLevel = MonitoringLevel.BASIC
    auto_rollback: bool = True  # 自动回滚失败交易
    alert_threshold: int = 10  # 告警阈值（失败交易数量）

@dataclass
class MonitoredTransaction:
    """被监控的交易"""
    signature: str
    trade_id: int
    user_address: str
    asset_id: int
    amount: float
    created_at: datetime
    last_check: Optional[datetime] = None
    status: TransactionStatus = TransactionStatus.SUBMITTED
    confirmations: int = 0
    retry_count: int = 0
    error_message: Optional[str] = None
    callback: Optional[Callable] = None

class TransactionMonitorService:
    """交易监控服务"""
    
    def __init__(self, config: TransactionMonitorConfig = None):
        self.config = config or TransactionMonitorConfig()
        self.monitored_transactions = {}  # signature -> MonitoredTransaction
        self.monitoring_thread = None
        self.is_monitoring = False
        self.statistics = {
            'total_monitored': 0,
            'confirmed': 0,
            'failed': 0,
            'timeout': 0,
            'rollbacks': 0
        }
        self._lock = threading.Lock()
        
    def start_monitoring(self):
        """启动交易监控"""
        if self.is_monitoring:
            logger.warning("交易监控已在运行")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("交易监控服务已启动")
    
    def stop_monitoring(self):
        """停止交易监控"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        logger.info("交易监控服务已停止")
    
    def add_transaction(
        self,
        signature: str,
        trade_id: int,
        user_address: str,
        asset_id: int,
        amount: float,
        callback: Callable = None
    ):
        """
        添加交易到监控列表
        
        Args:
            signature: 交易签名
            trade_id: 交易记录ID
            user_address: 用户地址
            asset_id: 资产ID
            amount: 交易金额
            callback: 状态变化回调函数
        """
        with self._lock:
            monitored_tx = MonitoredTransaction(
                signature=signature,
                trade_id=trade_id,
                user_address=user_address,
                asset_id=asset_id,
                amount=amount,
                created_at=datetime.utcnow(),
                callback=callback
            )
            
            self.monitored_transactions[signature] = monitored_tx
            self.statistics['total_monitored'] += 1
            
            logger.info(f"交易已添加到监控: {signature}")
    
    def remove_transaction(self, signature: str):
        """从监控列表中移除交易"""
        with self._lock:
            if signature in self.monitored_transactions:
                del self.monitored_transactions[signature]
                logger.debug(f"交易已从监控中移除: {signature}")
    
    def get_transaction_status(self, signature: str) -> Optional[Dict[str, Any]]:
        """获取被监控交易的状态"""
        with self._lock:
            if signature not in self.monitored_transactions:
                return None
            
            tx = self.monitored_transactions[signature]
            return {
                'signature': tx.signature,
                'trade_id': tx.trade_id,
                'status': tx.status.value,
                'confirmations': tx.confirmations,
                'created_at': tx.created_at.isoformat(),
                'last_check': tx.last_check.isoformat() if tx.last_check else None,
                'retry_count': tx.retry_count,
                'error_message': tx.error_message
            }
    
    def _monitoring_loop(self):
        """监控循环"""
        logger.info("交易监控循环已启动")
        
        while self.is_monitoring:
            try:
                self._check_all_transactions()
                self._cleanup_old_transactions()
                self._check_network_health()
                
                time.sleep(self.config.check_interval)
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(self.config.check_interval * 2)  # 出错时延长等待时间
    
    def _check_all_transactions(self):
        """检查所有被监控的交易"""
        with self._lock:
            transactions_to_check = list(self.monitored_transactions.values())
        
        for tx in transactions_to_check:
            try:
                self._check_single_transaction(tx)
            except Exception as e:
                logger.error(f"检查交易 {tx.signature} 时出错: {e}")
    
    def _check_single_transaction(self, tx: MonitoredTransaction):
        """检查单个交易状态"""
        try:
            # 检查是否超时
            if self._is_transaction_timeout(tx):
                self._handle_transaction_timeout(tx)
                return
            
            # 获取交易状态
            status_result = check_transaction_status(tx.signature)
            tx.last_check = datetime.utcnow()
            
            # 更新交易状态
            old_status = tx.status
            
            if status_result['confirmed']:
                tx.status = TransactionStatus.CONFIRMED
                tx.confirmations = status_result['confirmations']
                
                if old_status != TransactionStatus.CONFIRMED:
                    self._handle_transaction_confirmed(tx)
                    
            elif status_result.get('error'):
                tx.status = TransactionStatus.FAILED
                tx.error_message = str(status_result['error'])
                
                if old_status != TransactionStatus.FAILED:
                    self._handle_transaction_failed(tx)
            
            # 调用回调函数
            if tx.callback and old_status != tx.status:
                try:
                    tx.callback(tx.signature, tx.status, status_result)
                except Exception as callback_error:
                    logger.error(f"交易回调函数执行失败: {callback_error}")
                    
        except Exception as e:
            tx.retry_count += 1
            tx.error_message = str(e)
            logger.warning(f"检查交易状态失败: {tx.signature}, 重试次数: {tx.retry_count}, 错误: {e}")
            
            # 如果重试次数过多，标记为失败
            if tx.retry_count >= self.config.max_retries:
                tx.status = TransactionStatus.FAILED
                self._handle_transaction_failed(tx)
    
    def _is_transaction_timeout(self, tx: MonitoredTransaction) -> bool:
        """检查交易是否超时"""
        elapsed = (datetime.utcnow() - tx.created_at).total_seconds()
        return elapsed > self.config.timeout_threshold
    
    def _handle_transaction_confirmed(self, tx: MonitoredTransaction):
        """处理交易确认"""
        logger.info(f"交易已确认: {tx.signature}, 确认数: {tx.confirmations}")
        
        # 更新数据库中的交易状态
        try:
            trade = Trade.query.get(tx.trade_id)
            if trade:
                trade.status = 'confirmed'
                trade.tx_hash = tx.signature
                trade.confirmations = tx.confirmations
                trade.confirmed_at = datetime.utcnow()
                db.session.add(trade)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"更新交易状态失败: {e}")
        
        # 更新统计
        self.statistics['confirmed'] += 1
        
        # 从监控列表中移除
        self.remove_transaction(tx.signature)
    
    def _handle_transaction_failed(self, tx: MonitoredTransaction):
        """处理交易失败"""
        logger.warning(f"交易失败: {tx.signature}, 错误: {tx.error_message}")
        
        # 更新数据库中的交易状态
        try:
            trade = Trade.query.get(tx.trade_id)
            if trade:
                trade.status = 'failed'
                trade.error_message = tx.error_message
                trade.failed_at = datetime.utcnow()
                db.session.add(trade)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"更新交易状态失败: {e}")
        
        # 自动回滚（如果启用）
        if self.config.auto_rollback:
            self._trigger_auto_rollback(tx)
        
        # 更新统计
        self.statistics['failed'] += 1
        
        # 从监控列表中移除
        self.remove_transaction(tx.signature)
    
    def _handle_transaction_timeout(self, tx: MonitoredTransaction):
        """处理交易超时"""
        logger.warning(f"交易超时: {tx.signature}")
        
        tx.status = TransactionStatus.TIMEOUT
        
        # 更新数据库中的交易状态
        try:
            trade = Trade.query.get(tx.trade_id)
            if trade:
                trade.status = 'timeout'
                trade.error_message = '交易确认超时'
                trade.failed_at = datetime.utcnow()
                db.session.add(trade)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"更新交易状态失败: {e}")
        
        # 自动回滚（如果启用）
        if self.config.auto_rollback:
            self._trigger_auto_rollback(tx, RollbackReason.TIMEOUT)
        
        # 更新统计
        self.statistics['timeout'] += 1
        
        # 从监控列表中移除
        self.remove_transaction(tx.signature)
    
    def _trigger_auto_rollback(self, tx: MonitoredTransaction, reason: RollbackReason = RollbackReason.TRANSACTION_FAILED):
        """触发自动回滚"""
        try:
            logger.info(f"触发自动回滚: 交易 {tx.signature}, 原因: {reason.value}")
            
            # 创建回滚计划
            rollback_plan = rollback_manager.create_rollback_plan(
                transaction_id=f"auto_{tx.signature}",
                trade_id=tx.trade_id,
                reason=reason
            )
            
            # 执行回滚
            rollback_success = rollback_manager.execute_rollback(rollback_plan.transaction_id)
            
            if rollback_success:
                logger.info(f"自动回滚成功: {tx.signature}")
                self.statistics['rollbacks'] += 1
            else:
                logger.error(f"自动回滚失败: {tx.signature}")
                
        except Exception as e:
            logger.error(f"自动回滚出错: {e}")
    
    def _cleanup_old_transactions(self):
        """清理旧的交易记录"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        with self._lock:
            to_remove = []
            for signature, tx in self.monitored_transactions.items():
                if tx.created_at < cutoff_time:
                    to_remove.append(signature)
            
            for signature in to_remove:
                del self.monitored_transactions[signature]
            
            if to_remove:
                logger.debug(f"清理了 {len(to_remove)} 个旧交易记录")
    
    def _check_network_health(self):
        """检查网络健康状态"""
        try:
            health_report = get_network_health_report()
            healthy_nodes = health_report.get('healthy_nodes', 0)
            total_nodes = health_report.get('total_nodes', 1)
            
            health_ratio = healthy_nodes / total_nodes if total_nodes > 0 else 0
            
            if health_ratio < 0.5:  # 如果健康节点少于50%
                logger.warning(f"网络健康状况不佳: {healthy_nodes}/{total_nodes} 节点健康")
                
                # 可以在这里触发告警或采取其他措施
                
        except Exception as e:
            logger.debug(f"检查网络健康状态失败: {e}")
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        with self._lock:
            current_monitoring = len(self.monitored_transactions)
            
            # 按状态分组统计当前监控的交易
            status_counts = defaultdict(int)
            for tx in self.monitored_transactions.values():
                status_counts[tx.status.value] += 1
            
            return {
                'total_monitored': self.statistics['total_monitored'],
                'confirmed': self.statistics['confirmed'],
                'failed': self.statistics['failed'],
                'timeout': self.statistics['timeout'],
                'rollbacks': self.statistics['rollbacks'],
                'current_monitoring': current_monitoring,
                'status_breakdown': dict(status_counts),
                'success_rate': (
                    self.statistics['confirmed'] / max(1, self.statistics['total_monitored'])
                ) * 100,
                'last_updated': datetime.utcnow().isoformat()
            }
    
    def get_active_transactions(self) -> List[Dict[str, Any]]:
        """获取当前活跃的交易列表"""
        with self._lock:
            return [
                {
                    'signature': tx.signature,
                    'trade_id': tx.trade_id,
                    'user_address': tx.user_address,
                    'asset_id': tx.asset_id,
                    'amount': tx.amount,
                    'status': tx.status.value,
                    'confirmations': tx.confirmations,
                    'created_at': tx.created_at.isoformat(),
                    'last_check': tx.last_check.isoformat() if tx.last_check else None,
                    'retry_count': tx.retry_count,
                    'error_message': tx.error_message
                }
                for tx in self.monitored_transactions.values()
            ]
    
    def force_check_transaction(self, signature: str) -> Dict[str, Any]:
        """强制检查特定交易"""
        with self._lock:
            if signature not in self.monitored_transactions:
                return {'error': '交易不在监控列表中'}
            
            tx = self.monitored_transactions[signature]
        
        try:
            self._check_single_transaction(tx)
            return {
                'success': True,
                'status': tx.status.value,
                'confirmations': tx.confirmations,
                'last_check': tx.last_check.isoformat() if tx.last_check else None
            }
        except Exception as e:
            return {'error': str(e)}

# 全局交易监控服务实例
transaction_monitor = TransactionMonitorService()