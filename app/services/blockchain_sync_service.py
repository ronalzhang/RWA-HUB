#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
区块链数据同步服务 - 定期同步链上数据确保数据一致性
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from threading import Thread
import schedule

from flask import current_app
from app.extensions import db
from app.models import Asset, Trade
from app.models.asset import AssetStatus
from app.models.trade import TradeStatus
from app.blockchain.solana_service import check_transaction
from app.services.data_consistency_manager import DataConsistencyManager

logger = logging.getLogger(__name__)

class BlockchainSyncService:
    """区块链数据同步服务"""
    
    def __init__(self):
        self.data_manager = DataConsistencyManager()
        self.sync_interval = 300  # 5分钟同步一次
        self.is_running = False
        self.sync_thread = None
    
    def start_sync_service(self):
        """启动同步服务"""
        if self.is_running:
            logger.warning("同步服务已在运行")
            return
        
        self.is_running = True
        
        # 设置定时任务
        schedule.every(5).minutes.do(self.sync_all_assets)
        schedule.every(2).minutes.do(self.sync_pending_trades)
        schedule.every(10).minutes.do(self.validate_data_consistency)
        
        # 启动后台线程
        self.sync_thread = Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()
        
        logger.info("区块链数据同步服务已启动")
    
    def stop_sync_service(self):
        """停止同步服务"""
        self.is_running = False
        schedule.clear()
        logger.info("区块链数据同步服务已停止")
    
    def _run_scheduler(self):
        """运行调度器"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"调度器运行错误: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟再继续
    
    def sync_all_assets(self):
        """同步所有资产数据"""
        try:
            logger.info("开始同步所有资产数据")
            
            # 获取所有已上链的资产
            assets = Asset.query.filter(
                Asset.status == AssetStatus.ON_CHAIN.value,
                Asset.token_address.isnot(None)
            ).all()
            
            sync_count = 0
            error_count = 0
            
            for asset in assets:
                try:
                    result = self.data_manager.sync_blockchain_data(asset.id)
                    if result['success']:
                        sync_count += 1
                    else:
                        error_count += 1
                        logger.warning(f"资产同步失败: {asset.id} - {result.get('error')}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"同步资产 {asset.id} 时出错: {str(e)}")
            
            logger.info(f"资产数据同步完成: 成功={sync_count}, 失败={error_count}")
            
        except Exception as e:
            logger.error(f"同步所有资产数据失败: {str(e)}")
    
    def sync_pending_trades(self):
        """同步待处理交易状态"""
        try:
            logger.info("开始同步待处理交易状态")
            
            # 获取所有待处理的交易
            pending_trades = Trade.query.filter(
                Trade.status == TradeStatus.PENDING.value,
                Trade.tx_hash.isnot(None)
            ).all()
            
            updated_count = 0
            
            for trade in pending_trades:
                try:
                    # 检查交易状态
                    tx_status = check_transaction(trade.tx_hash)
                    
                    if tx_status.get('confirmed', False):
                        # 交易已确认，更新状态
                        with db.session.begin():
                            trade.status = TradeStatus.COMPLETED.value
                            
                            # 更新资产数据
                            self.data_manager.update_asset_after_trade(trade.id)
                            
                            db.session.commit()
                            
                        updated_count += 1
                        logger.info(f"交易状态已更新: {trade.id} -> COMPLETED")
                        
                    elif tx_status.get('error'):
                        # 交易失败
                        trade.status = TradeStatus.FAILED.value
                        db.session.commit()
                        
                        logger.warning(f"交易失败: {trade.id} - {tx_status['error']}")
                        
                except Exception as e:
                    logger.error(f"检查交易 {trade.id} 状态时出错: {str(e)}")
            
            if updated_count > 0:
                logger.info(f"交易状态同步完成: 更新了 {updated_count} 个交易")
            
        except Exception as e:
            logger.error(f"同步待处理交易失败: {str(e)}")
    
    def validate_data_consistency(self):
        """验证数据一致性"""
        try:
            logger.info("开始验证数据一致性")
            
            # 获取所有活跃资产
            assets = Asset.query.filter(
                Asset.status.in_([AssetStatus.ON_CHAIN.value, AssetStatus.CONFIRMED.value]),
                Asset.deleted_at.is_(None)
            ).all()
            
            total_issues = 0
            
            for asset in assets:
                try:
                    result = self.data_manager.validate_data_consistency(asset.id)
                    if result['success'] and result['issues_found'] > 0:
                        total_issues += result['issues_found']
                        logger.warning(f"资产 {asset.id} 发现 {result['issues_found']} 个数据一致性问题")
                        
                except Exception as e:
                    logger.error(f"验证资产 {asset.id} 数据一致性时出错: {str(e)}")
            
            if total_issues > 0:
                logger.warning(f"数据一致性验证完成: 发现并修复了 {total_issues} 个问题")
            else:
                logger.info("数据一致性验证完成: 未发现问题")
            
        except Exception as e:
            logger.error(f"数据一致性验证失败: {str(e)}")
    
    def force_sync_asset(self, asset_id: int) -> Dict[str, Any]:
        """
        强制同步指定资产
        
        Args:
            asset_id: 资产ID
            
        Returns:
            Dict: 同步结果
        """
        try:
            logger.info(f"强制同步资产: {asset_id}")
            
            # 同步区块链数据
            sync_result = self.data_manager.sync_blockchain_data(asset_id)
            
            # 验证数据一致性
            validation_result = self.data_manager.validate_data_consistency(asset_id)
            
            return {
                'success': True,
                'asset_id': asset_id,
                'sync_result': sync_result,
                'validation_result': validation_result,
                'synced_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"强制同步资产失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步服务状态
        
        Returns:
            Dict: 服务状态信息
        """
        try:
            # 统计待同步数据
            pending_trades_count = Trade.query.filter(
                Trade.status == TradeStatus.PENDING.value,
                Trade.tx_hash.isnot(None)
            ).count()
            
            active_assets_count = Asset.query.filter(
                Asset.status == AssetStatus.ON_CHAIN.value,
                Asset.token_address.isnot(None)
            ).count()
            
            return {
                'service_running': self.is_running,
                'sync_interval': self.sync_interval,
                'pending_trades': pending_trades_count,
                'active_assets': active_assets_count,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取同步状态失败: {str(e)}")
            return {
                'service_running': self.is_running,
                'error': str(e)
            }

# 全局同步服务实例
sync_service = BlockchainSyncService()

def init_sync_service(app):
    """初始化同步服务"""
    with app.app_context():
        sync_service.start_sync_service()

def get_sync_service():
    """获取同步服务实例"""
    return sync_service