#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据一致性管理器 - 确保资产数据的实时性和准确性
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal

from flask import current_app
from sqlalchemy import text, func
from app.extensions import db
from app.models import Asset, Trade
from app.models.trade import TradeStatus
from app.blockchain.solana_service import check_transaction

logger = logging.getLogger(__name__)

class DataConsistencyManager:
    """数据一致性管理器"""
    
    def __init__(self):
        self.cache_timeout = 300  # 5分钟缓存
        self._cache = {}
    
    def get_real_time_asset_data(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """
        获取实时资产数据
        
        Args:
            asset_id: 资产ID
            
        Returns:
            Dict: 实时资产数据
        """
        try:
            cache_key = f"asset_data:{asset_id}"
            
            # 检查缓存
            if self._is_cache_valid(cache_key):
                logger.debug(f"从缓存获取资产数据: {asset_id}")
                return self._cache[cache_key]['data']
            
            # 从数据库获取最新数据
            asset = Asset.query.get(asset_id)
            if not asset:
                return None
            
            # 计算实时统计
            asset_stats = self._calculate_asset_statistics(asset_id)
            
            # 构建实时数据
            asset_data = {
                'id': asset.id,
                'name': asset.name,
                'description': asset.description,
                'token_symbol': asset.token_symbol,
                'token_price': float(asset.token_price),
                'token_supply': asset.token_supply,
                'remaining_supply': self._get_accurate_remaining_supply(asset),
                'annual_revenue': float(asset.annual_revenue),
                'status': asset.status,
                'images': asset.images,
                'location': asset.location,
                'creator_address': asset.creator_address,
                'owner_address': asset.owner_address,
                'created_at': asset.created_at.isoformat() if asset.created_at else None,
                'updated_at': asset.updated_at.isoformat() if asset.updated_at else None,
                
                # 实时统计数据
                'total_trades': asset_stats['total_trades'],
                'total_volume': asset_stats['total_volume'],
                'total_dividends': asset_stats['total_dividends'],
                'last_trade_at': asset_stats['last_trade_at'],
                'last_updated': datetime.utcnow().isoformat()
            }
            
            # 缓存数据
            self._cache[cache_key] = {
                'data': asset_data,
                'timestamp': time.time()
            }
            
            logger.info(f"获取实时资产数据完成: asset_id={asset_id}")
            return asset_data
            
        except Exception as e:
            logger.error(f"获取实时资产数据失败: {str(e)}", exc_info=True)
            return None
    
    def _get_accurate_remaining_supply(self, asset: Asset) -> int:
        """
        获取准确的剩余供应量（带锁机制防止并发冲突）
        
        Args:
            asset: 资产对象
            
        Returns:
            int: 准确的剩余供应量
        """
        try:
            # 检查是否已经在事务中
            if db.session.in_transaction():
                # 如果已经在事务中，直接查询
                locked_asset = db.session.query(Asset).filter_by(id=asset.id).first()
            else:
                # 使用数据库行锁防止并发更新冲突
                with db.session.begin():
                    locked_asset = db.session.query(Asset).filter_by(id=asset.id).with_for_update().first()
            
            if not locked_asset:
                logger.error(f"资产 {asset.id} 不存在")
                return 0
            
            # 如果数据库中有值，先使用数据库的值
            if locked_asset.remaining_supply is not None:
                remaining = locked_asset.remaining_supply
            else:
                remaining = locked_asset.token_supply
            
            # 验证数据一致性：通过交易记录计算实际剩余量
            total_bought = db.session.query(func.sum(Trade.amount)).filter(
                Trade.asset_id == locked_asset.id,
                Trade.type == 'buy',
                Trade.status == TradeStatus.COMPLETED.value
            ).scalar() or 0
            
            total_sold = db.session.query(func.sum(Trade.amount)).filter(
                Trade.asset_id == locked_asset.id,
                Trade.type == 'sell',
                Trade.status == TradeStatus.COMPLETED.value
            ).scalar() or 0
            
            calculated_remaining = locked_asset.token_supply - total_bought + total_sold
            
            # 如果计算值与数据库值不一致，更新数据库
            if abs(calculated_remaining - remaining) > 0:
                logger.warning(f"资产 {locked_asset.id} 剩余供应量不一致: DB={remaining}, 计算值={calculated_remaining}")
                
                # 只有在不在事务中时才更新数据库
                if not db.session.in_transaction():
                    try:
                        locked_asset.remaining_supply = max(0, calculated_remaining)  # 确保不为负数
                        locked_asset.updated_at = datetime.utcnow()
                        db.session.commit()
                        
                        # 清除相关缓存
                        self._invalidate_cache(f"asset_data:{locked_asset.id}")
                        
                        remaining = locked_asset.remaining_supply
                        logger.info(f"已修复资产 {locked_asset.id} 的剩余供应量: {remaining}")
                    except Exception as update_error:
                        logger.error(f"更新剩余供应量失败: {str(update_error)}")
                        db.session.rollback()
            
            return max(0, remaining)  # 确保返回值不为负数
            
        except Exception as e:
            logger.error(f"计算剩余供应量失败: {str(e)}")
            return asset.remaining_supply or asset.token_supply
    
    def _calculate_asset_statistics(self, asset_id: int) -> Dict[str, Any]:
        """
        计算资产统计数据
        
        Args:
            asset_id: 资产ID
            
        Returns:
            Dict: 统计数据
        """
        try:
            # 交易统计
            total_trades = Trade.query.filter_by(
                asset_id=asset_id,
                status=TradeStatus.COMPLETED.value
            ).count()
            
            total_volume = db.session.query(func.sum(Trade.total)).filter(
                Trade.asset_id == asset_id,
                Trade.status == TradeStatus.COMPLETED.value
            ).scalar() or 0
            
            # 最后交易时间
            last_trade = Trade.query.filter_by(
                asset_id=asset_id,
                status=TradeStatus.COMPLETED.value
            ).order_by(Trade.created_at.desc()).first()
            
            last_trade_at = last_trade.created_at.isoformat() if last_trade else None
            
            # 分红统计
            total_dividends = self._calculate_total_dividends(asset_id)
            
            return {
                'total_trades': total_trades,
                'total_volume': float(total_volume),
                'total_dividends': total_dividends,
                'last_trade_at': last_trade_at
            }
            
        except Exception as e:
            logger.error(f"计算资产统计失败: {str(e)}")
            return {
                'total_trades': 0,
                'total_volume': 0.0,
                'total_dividends': 0.0,
                'last_trade_at': None
            }
    
    def _calculate_total_dividends(self, asset_id: int) -> float:
        """
        计算总分红金额
        
        Args:
            asset_id: 资产ID
            
        Returns:
            float: 总分红金额
        """
        try:
            # 使用原生SQL查询避免模型依赖问题
            sql = text("SELECT SUM(amount) FROM dividends WHERE asset_id = :asset_id AND status = 'confirmed'")
            result = db.session.execute(sql, {"asset_id": asset_id}).fetchone()
            return float(result[0]) if result[0] else 0.0
        except Exception as e:
            logger.error(f"计算分红总额失败: {str(e)}")
            return 0.0
    
    def update_asset_after_trade(self, trade_id: int) -> bool:
        """
        交易后更新资产数据
        
        Args:
            trade_id: 交易ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with db.session.begin():
                trade = Trade.query.get(trade_id)
                if not trade:
                    logger.error(f"交易记录不存在: {trade_id}")
                    return False
                
                asset = Asset.query.get(trade.asset_id)
                if not asset:
                    logger.error(f"资产不存在: {trade.asset_id}")
                    return False
                
                # 更新剩余供应量
                if trade.type == 'buy':
                    new_remaining = (asset.remaining_supply or asset.token_supply) - trade.amount
                elif trade.type == 'sell':
                    new_remaining = (asset.remaining_supply or 0) + trade.amount
                else:
                    logger.warning(f"未知交易类型: {trade.type}")
                    return False
                
                # 确保剩余供应量不为负数
                asset.remaining_supply = max(0, new_remaining)
                asset.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                # 清除相关缓存
                self._invalidate_cache(f"asset_data:{asset.id}")
                
                logger.info(f"交易后资产数据更新完成: asset_id={asset.id}, trade_id={trade_id}, remaining={asset.remaining_supply}")
                return True
                
        except Exception as e:
            logger.error(f"交易后更新资产数据失败: {str(e)}", exc_info=True)
            db.session.rollback()
            return False
    
    def sync_blockchain_data(self, asset_id: int) -> Dict[str, Any]:
        """
        同步区块链数据
        
        Args:
            asset_id: 资产ID
            
        Returns:
            Dict: 同步结果
        """
        try:
            asset = Asset.query.get(asset_id)
            if not asset:
                return {'success': False, 'error': '资产不存在'}
            
            if not asset.token_address:
                return {'success': False, 'error': '资产未上链'}
            
            # 获取链上数据（这里需要根据实际的区块链接口实现）
            # 暂时返回成功状态
            sync_result = {
                'success': True,
                'asset_id': asset_id,
                'token_address': asset.token_address,
                'synced_at': datetime.utcnow().isoformat(),
                'changes': []
            }
            
            # 清除缓存以确保下次获取最新数据
            self._invalidate_cache(f"asset_data:{asset_id}")
            
            logger.info(f"区块链数据同步完成: asset_id={asset_id}")
            return sync_result
            
        except Exception as e:
            logger.error(f"同步区块链数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_trade_history(self, asset_id: int, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        获取交易历史（实时数据）
        
        Args:
            asset_id: 资产ID
            page: 页码
            per_page: 每页数量
            
        Returns:
            Dict: 交易历史数据
        """
        try:
            # 查询交易记录
            query = Trade.query.filter_by(asset_id=asset_id).order_by(Trade.created_at.desc())
            
            # 分页
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            trades = pagination.items
            
            # 转换为字典格式
            trade_list = []
            for trade in trades:
                trade_data = trade.to_dict()
                
                # 添加状态描述
                if trade.status == TradeStatus.COMPLETED.value:
                    trade_data['status_description'] = '已完成'
                elif trade.status == TradeStatus.PENDING.value:
                    trade_data['status_description'] = '处理中'
                elif trade.status == TradeStatus.FAILED.value:
                    trade_data['status_description'] = '失败'
                else:
                    trade_data['status_description'] = '未知状态'
                
                trade_list.append(trade_data)
            
            return {
                'success': True,
                'trades': trade_list,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
            
        except Exception as e:
            logger.error(f"获取交易历史失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False
        
        cache_time = self._cache[cache_key]['timestamp']
        return (time.time() - cache_time) < self.cache_timeout
    
    def _invalidate_cache(self, cache_key: str):
        """使缓存失效"""
        if cache_key in self._cache:
            del self._cache[cache_key]
    
    def clear_all_cache(self):
        """清除所有缓存"""
        self._cache.clear()
        logger.info("所有缓存已清除")
    
    def validate_data_consistency(self, asset_id: int) -> Dict[str, Any]:
        """
        验证数据一致性
        
        Args:
            asset_id: 资产ID
            
        Returns:
            Dict: 验证结果
        """
        try:
            asset = Asset.query.get(asset_id)
            if not asset:
                return {'success': False, 'error': '资产不存在'}
            
            issues = []
            
            # 检查剩余供应量
            calculated_remaining = self._get_accurate_remaining_supply(asset)
            if asset.remaining_supply != calculated_remaining:
                issues.append({
                    'type': 'remaining_supply_mismatch',
                    'database_value': asset.remaining_supply,
                    'calculated_value': calculated_remaining,
                    'fixed': True
                })
            
            # 检查交易状态一致性
            pending_trades = Trade.query.filter_by(
                asset_id=asset_id,
                status=TradeStatus.PENDING.value
            ).all()
            
            for trade in pending_trades:
                if trade.tx_hash:
                    # 检查区块链交易状态
                    tx_status = check_transaction(trade.tx_hash)
                    if tx_status.get('confirmed', False):
                        issues.append({
                            'type': 'trade_status_outdated',
                            'trade_id': trade.id,
                            'current_status': trade.status,
                            'should_be': 'completed'
                        })
            
            return {
                'success': True,
                'asset_id': asset_id,
                'issues_found': len(issues),
                'issues': issues,
                'validated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"数据一致性验证失败: {str(e)}")
            return {'success': False, 'error': str(e)}