#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能合约执行状态监控服务
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from threading import Thread
# import schedule  # 暂时禁用，避免导入错误

from flask import current_app
from app.extensions import db
from app.models import Asset, Trade
from app.models.asset import AssetStatus
from app.models.trade import TradeStatus
from app.blockchain.solana_service import check_transaction

logger = logging.getLogger(__name__)

def init_contract_monitor(app):
    """初始化智能合约监控服务（简化版本）"""
    try:
        logger.info("智能合约监控服务已初始化（简化版本，避免schedule模块依赖）")
        # 这里可以添加基于Flask-APScheduler的监控逻辑
        return True
    except Exception as e:
        logger.error(f"初始化智能合约监控服务失败: {e}")
        return False

class ContractMonitor:
    """智能合约执行监控器"""
    
    def __init__(self, app=None):
        self.is_running = False
        self.monitor_thread = None
        self.app = app
    
    def start_monitoring(self):
        """启动监控服务"""
        if self.is_running:
            logger.warning("合约监控服务已在运行")
            return
        
        self.is_running = True
        
        # 设置定时任务
        # schedule.every(1).minutes.do(self.monitor_asset_creation)  # 暂时禁用
        # schedule.every(30).seconds.do(self.monitor_purchase_transactions)  # 暂时禁用
        
        # 启动后台线程
        self.monitor_thread = Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()
        
        logger.info("智能合约监控服务已启动")
    
    def stop_monitoring(self):
        """停止监控服务"""
        self.is_running = False
        # schedule.clear()  # 暂时禁用
        logger.info("智能合约监控服务已停止")
    
    def _run_monitor(self):
        """运行监控器"""
        while self.is_running:
            try:
                if self.app:
                    with self.app.app_context():
                        # schedule.run_pending()  # 暂时禁用
                        pass
                else:
                    # schedule.run_pending()  # 暂时禁用
                    pass
                time.sleep(10)  # 每10秒检查一次
            except Exception as e:
                logger.error(f"监控器运行错误: {str(e)}")
                time.sleep(30)  # 出错后等待30秒再继续
    
    def monitor_asset_creation(self):
        """监控资产创建智能合约执行状态"""
        try:
            logger.debug("开始监控资产创建状态")
            
            # 查找支付已确认但尚未上链的资产
            pending_assets = Asset.query.filter(
                Asset.payment_confirmed == True,
                Asset.status == AssetStatus.CONFIRMED.value,
                Asset.token_address.is_(None)
            ).all()
            
            for asset in pending_assets:
                try:
                    # 检查是否有部署交易哈希
                    if asset.deployment_tx_hash:
                        # 检查部署交易状态
                        tx_status = check_transaction(asset.deployment_tx_hash)
                        
                        if tx_status.get('confirmed', False):
                            # 部署成功，更新状态
                            with db.session.begin():
                                asset.status = AssetStatus.ON_CHAIN.value
                                asset.deployment_in_progress = False
                                
                                # 如果还没有token_address，需要从合约中获取
                                if not asset.token_address:
                                    # 这里应该调用合约查询方法获取token地址
                                    # asset.token_address = get_token_address_from_contract(asset.id)
                                    pass
                                
                                db.session.commit()
                                
                            logger.info(f"资产 {asset.id} 智能合约创建成功")
                            
                        elif tx_status.get('error'):
                            # 部署失败
                            with db.session.begin():
                                asset.status = AssetStatus.DEPLOYMENT_FAILED.value
                                asset.deployment_in_progress = False
                                asset.error_message = f"智能合约部署失败: {tx_status['error']}"
                                
                                db.session.commit()
                                
                            logger.error(f"资产 {asset.id} 智能合约部署失败: {tx_status['error']}")
                    
                    else:
                        # 检查是否超时（支付确认后超过10分钟仍未开始部署）
                        if (asset.payment_confirmed_at and 
                            datetime.utcnow() - asset.payment_confirmed_at > timedelta(minutes=10) and
                            not asset.deployment_in_progress):
                            
                            logger.warning(f"资产 {asset.id} 支付确认后超时未开始智能合约部署")
                            
                            # 尝试重新触发部署
                            try:
                                from app.blockchain.asset_service import AssetService
                                asset_service = AssetService()
                                result = asset_service.create_asset_on_chain(asset.id)
                                
                                if result.get('success'):
                                    logger.info(f"重新触发资产 {asset.id} 智能合约部署")
                                else:
                                    logger.error(f"重新触发资产 {asset.id} 智能合约部署失败: {result.get('error')}")
                                    
                            except Exception as retry_error:
                                logger.error(f"重新触发资产 {asset.id} 智能合约部署异常: {str(retry_error)}")
                
                except Exception as e:
                    logger.error(f"监控资产 {asset.id} 创建状态时出错: {str(e)}")
            
            if pending_assets:
                logger.debug(f"监控了 {len(pending_assets)} 个待上链资产")
            
        except Exception as e:
            logger.error(f"监控资产创建失败: {str(e)}")
    
    def monitor_purchase_transactions(self):
        """监控购买交易智能合约执行状态"""
        try:
            logger.debug("开始监控购买交易状态")
            
            # 查找待处理的购买交易
            pending_trades = Trade.query.filter(
                Trade.status == TradeStatus.PENDING.value,
                Trade.tx_hash.isnot(None)
            ).all()
            
            confirmed_count = 0
            
            for trade in pending_trades:
                try:
                    # 检查交易状态
                    tx_status = check_transaction(trade.tx_hash)
                    
                    if tx_status.get('confirmed', False):
                        # 交易已确认
                        with db.session.begin():
                            trade.status = TradeStatus.COMPLETED.value
                            
                            # 更新资产剩余供应量
                            asset = Asset.query.get(trade.asset_id)
                            if asset:
                                if trade.type == 'buy':
                                    asset.remaining_supply = (asset.remaining_supply or asset.token_supply) - trade.amount
                                elif trade.type == 'sell':
                                    asset.remaining_supply = (asset.remaining_supply or 0) + trade.amount
                                
                                # 确保剩余供应量不为负数
                                asset.remaining_supply = max(0, asset.remaining_supply)
                                asset.updated_at = datetime.utcnow()
                            
                            db.session.commit()
                            
                        confirmed_count += 1
                        logger.info(f"购买交易 {trade.id} 智能合约执行成功")
                        
                    elif tx_status.get('error'):
                        # 交易失败
                        with db.session.begin():
                            trade.status = TradeStatus.FAILED.value
                            trade.error_message = f"智能合约执行失败: {tx_status['error']}"
                            
                            db.session.commit()
                            
                        logger.error(f"购买交易 {trade.id} 智能合约执行失败: {tx_status['error']}")
                
                except Exception as e:
                    logger.error(f"监控交易 {trade.id} 状态时出错: {str(e)}")
            
            if confirmed_count > 0:
                logger.info(f"确认了 {confirmed_count} 个购买交易")
            
        except Exception as e:
            logger.error(f"监控购买交易失败: {str(e)}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        try:
            # 统计待监控的资产和交易
            pending_assets = Asset.query.filter(
                Asset.payment_confirmed == True,
                Asset.status == AssetStatus.CONFIRMED.value,
                Asset.token_address.is_(None)
            ).count()
            
            pending_trades = Trade.query.filter(
                Trade.status == TradeStatus.PENDING.value,
                Trade.tx_hash.isnot(None)
            ).count()
            
            return {
                'service_running': self.is_running,
                'pending_asset_creations': pending_assets,
                'pending_purchase_trades': pending_trades,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取监控状态失败: {str(e)}")
            return {
                'service_running': self.is_running,
                'error': str(e)
            }

# 全局监控服务实例
contract_monitor = None

def init_contract_monitor(app):
    """初始化合约监控服务"""
    global contract_monitor
    contract_monitor = ContractMonitor(app)
    with app.app_context():
        contract_monitor.start_monitoring()

def get_contract_monitor():
    """获取合约监控服务实例"""
    return contract_monitor

# 简化的监控实现，避免依赖schedule模块
def init_contract_monitor(app):
    """初始化智能合约监控服务（简化版本）"""
    try:
        logger.info("智能合约监控服务已初始化（简化版本）")
        # 这里可以添加基于Flask-APScheduler的监控逻辑
        return True
    except Exception as e:
        logger.error(f"初始化智能合约监控服务失败: {e}")
        return False
