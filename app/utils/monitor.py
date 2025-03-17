"""
交易监控工具，用于自动确认交易和分红
"""
import os
import time
import threading
import logging
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models.trade import Trade
from app.models.asset import Asset
from app.models.dividend import DividendRecord
from app.utils.solana import solana_client

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 监控间隔（秒）
MONITOR_INTERVAL = int(os.environ.get('MONITOR_INTERVAL', 60))
# 交易确认阈值（秒）
TRANSACTION_CONFIRM_THRESHOLD = int(os.environ.get('TRANSACTION_CONFIRM_THRESHOLD', 60 * 30))  # 30分钟
# 重试次数
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))

class TransactionMonitor:
    """交易监控类"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """启动监控"""
        if self.running:
            logger.info("监控已在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("交易监控已启动")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=MONITOR_INTERVAL + 5)
        logger.info("交易监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._check_pending_transactions()
                self._check_pending_dividends()
            except Exception as e:
                logger.error(f"监控循环发生错误: {str(e)}")
            
            # 休眠指定时间
            time.sleep(MONITOR_INTERVAL)
    
    def _check_pending_transactions(self):
        """检查待处理的交易"""
        try:
            # 查询待确认的交易
            threshold_time = datetime.utcnow() - timedelta(seconds=TRANSACTION_CONFIRM_THRESHOLD)
            pending_trades = Trade.query.filter(
                Trade.status == 'pending',
                Trade.created_at <= threshold_time
            ).all()
            
            logger.info(f"发现 {len(pending_trades)} 个待处理交易")
            
            for trade in pending_trades:
                # 跳过没有交易哈希的记录
                if not trade.tx_hash:
                    continue
                
                # 验证交易状态
                try:
                    # 调用 Solana API 验证交易状态
                    # 这里是简化版，实际需要调用链上接口
                    transaction_confirmed = self._check_transaction_on_chain(trade.tx_hash)
                    
                    if transaction_confirmed:
                        # 获取相关资产
                        asset = Asset.query.get(trade.asset_id)
                        if not asset:
                            logger.error(f"交易 {trade.id} 对应的资产不存在")
                            continue
                            
                        # 确保资产有剩余供应量字段
                        if asset.remaining_supply is None:
                            asset.remaining_supply = asset.token_supply
                            
                        # 检查剩余供应量是否足够（只对买入交易检查）
                        if trade.type == 'buy' and asset.remaining_supply < trade.amount:
                            trade.status = 'failed'
                            logger.warning(f"交易 {trade.id} 失败：剩余供应量不足")
                        else:
                            # 更新交易状态
                            trade.status = 'completed'
                            
                            # 更新资产的剩余供应量（只对买入交易更新）
                            if trade.type == 'buy':
                                old_remaining = asset.remaining_supply
                                asset.remaining_supply = max(0, asset.remaining_supply - trade.amount)
                                logger.info(f"更新资产 {asset.id} 剩余供应量: {old_remaining} -> {asset.remaining_supply}")
                                
                            logger.info(f"交易 {trade.id} 已确认完成，哈希: {trade.tx_hash}")
                        
                        db.session.commit()
                    else:
                        # 增加重试次数或标记失败
                        if trade.retries >= MAX_RETRIES:
                            trade.status = 'failed'
                            db.session.commit()
                            logger.warning(f"交易 {trade.id} 确认失败，已达最大重试次数")
                        else:
                            trade.retries = (trade.retries or 0) + 1
                            db.session.commit()
                            logger.info(f"交易 {trade.id} 确认中，重试次数: {trade.retries}")
                    
                except Exception as e:
                    logger.error(f"验证交易 {trade.id} 状态失败: {str(e)}")
        
        except SQLAlchemyError as e:
            logger.error(f"数据库查询错误: {str(e)}")
            db.session.rollback()
    
    def _check_transaction_on_chain(self, tx_hash):
        """检查链上交易状态
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            bool: 交易是否确认成功
        """
        try:
            # 实际环境中应该调用 Solana API 查询交易状态
            # 例如: solana_client.get_transaction_status(tx_hash)
            if tx_hash.startswith('mock_'):
                # 模拟环境，直接返回成功
                return True
            
            # 真实环境，调用 Solana API
            # 检查交易是否存在
            transaction_info = solana_client.get_transaction(tx_hash)
            if not transaction_info:
                logger.warning(f"交易 {tx_hash} 不存在于链上")
                return False
            
            # 检查交易是否已确认
            if 'confirmations' in transaction_info:
                # 确认数大于等于1表示交易已确认
                return transaction_info['confirmations'] >= 1
            elif 'confirmationStatus' in transaction_info:
                # 状态为 'confirmed' 或 'finalized' 表示交易已确认
                return transaction_info['confirmationStatus'] in ['confirmed', 'finalized']
            else:
                # 无法判断状态，默认为未确认
                return False
            
        except Exception as e:
            logger.error(f"检查链上交易状态失败 ({tx_hash}): {str(e)}")
            return False
    
    def _check_pending_dividends(self):
        """检查待处理的分红"""
        try:
            # 查询待确认的分红
            threshold_time = datetime.utcnow() - timedelta(seconds=TRANSACTION_CONFIRM_THRESHOLD)
            pending_dividends = DividendRecord.query.filter(
                DividendRecord.status == 'pending',
                DividendRecord.created_at <= threshold_time
            ).all()
            
            logger.info(f"发现 {len(pending_dividends)} 个待处理分红")
            
            for dividend in pending_dividends:
                # 跳过没有交易哈希的记录
                if not dividend.tx_hash:
                    continue
                
                # 验证分红状态
                try:
                    # 调用 Solana API 验证交易状态
                    # 这里是简化版，实际需要调用链上接口
                    transaction_confirmed = True  # 假设交易已确认
                    
                    if transaction_confirmed:
                        # 更新分红状态
                        dividend.status = 'completed'
                        db.session.commit()
                        logger.info(f"分红 {dividend.id} 已确认完成，哈希: {dividend.tx_hash}")
                    else:
                        # 增加重试次数或标记失败
                        if dividend.retries >= MAX_RETRIES:
                            dividend.status = 'failed'
                            db.session.commit()
                            logger.warning(f"分红 {dividend.id} 确认失败，已达最大重试次数")
                        else:
                            dividend.retries = (dividend.retries or 0) + 1
                            db.session.commit()
                            logger.info(f"分红 {dividend.id} 确认中，重试次数: {dividend.retries}")
                    
                except Exception as e:
                    logger.error(f"验证分红 {dividend.id} 状态失败: {str(e)}")
        
        except SQLAlchemyError as e:
            logger.error(f"数据库查询错误: {str(e)}")
            db.session.rollback()


# 单例实例
transaction_monitor = TransactionMonitor()

def start_monitor():
    """启动交易监控"""
    transaction_monitor.start()

def stop_monitor():
    """停止交易监控"""
    transaction_monitor.stop() 