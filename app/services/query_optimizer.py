#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查询优化器 - 任务5.3优化数据库查询性能
提供优化的数据库查询方法和缓存机制
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from functools import wraps
from sqlalchemy import text, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload

from flask import current_app
from app.extensions import db
from app.models import Asset, Trade, User
from app.models.asset import AssetStatus, AssetType
from app.models.trade import TradeStatus, TradeType

logger = logging.getLogger(__name__)

def query_cache(timeout: int = 300):
    """
    查询结果缓存装饰器
    
    Args:
        timeout: 缓存超时时间（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 生成缓存键
            cache_key = f"query_cache:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 尝试从缓存获取
            if hasattr(self, '_redis_client') and self._redis_client:
                try:
                    cached_result = self._redis_client.get(cache_key)
                    if cached_result:
                        logger.debug(f"从缓存获取查询结果: {func.__name__}")
                        return json.loads(cached_result)
                except Exception as cache_error:
                    logger.warning(f"缓存获取失败: {str(cache_error)}")
            
            # 执行查询
            result = func(self, *args, **kwargs)
            
            # 缓存结果
            if hasattr(self, '_redis_client') and self._redis_client and result:
                try:
                    self._redis_client.setex(cache_key, timeout, json.dumps(result, default=str))
                    logger.debug(f"查询结果已缓存: {func.__name__}")
                except Exception as cache_error:
                    logger.warning(f"缓存设置失败: {str(cache_error)}")
            
            return result
        return wrapper
    return decorator

class QueryOptimizer:
    """查询优化器 - 实现任务5.3核心功能"""
    
    def __init__(self):
        self._redis_client = None
        self._init_redis()
        self.query_stats = {}  # 查询性能统计
        
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            import redis
            redis_url = getattr(current_app.config, 'REDIS_URL', 'redis://localhost:6379/0')
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            self._redis_client.ping()
            logger.info("QueryOptimizer Redis连接成功")
        except Exception as e:
            logger.warning(f"QueryOptimizer Redis连接失败，使用无缓存模式: {str(e)}")
            self._redis_client = None
    
    def _track_query_performance(self, query_name: str, duration: float, result_count: int = 0):
        """跟踪查询性能"""
        if query_name not in self.query_stats:
            self.query_stats[query_name] = {
                'total_calls': 0,
                'total_duration': 0,
                'avg_duration': 0,
                'max_duration': 0,
                'min_duration': float('inf'),
                'total_results': 0
            }
        
        stats = self.query_stats[query_name]
        stats['total_calls'] += 1
        stats['total_duration'] += duration
        stats['avg_duration'] = stats['total_duration'] / stats['total_calls']
        stats['max_duration'] = max(stats['max_duration'], duration)
        stats['min_duration'] = min(stats['min_duration'], duration)
        stats['total_results'] += result_count
        
        # 记录慢查询
        if duration > 1.0:  # 超过1秒的查询
            logger.warning(f"慢查询检测: {query_name}, 耗时: {duration:.2f}s, 结果数: {result_count}")
    
    @query_cache(timeout=300)
    def get_optimized_asset_list(self, page: int = 1, per_page: int = 20, 
                                status: Optional[str] = None, 
                                asset_type: Optional[int] = None,
                                creator_address: Optional[str] = None) -> Dict[str, Any]:
        """
        优化的资产列表查询
        
        Args:
            page: 页码
            per_page: 每页数量
            status: 资产状态过滤
            asset_type: 资产类型过滤
            creator_address: 创建者地址过滤
            
        Returns:
            Dict: 分页的资产列表数据
        """
        start_time = time.time()
        
        try:
            # 构建优化的查询
            query = db.session.query(Asset).options(
                # 预加载相关数据，减少N+1查询问题
                selectinload(Asset.trades.and_(Trade.status == TradeStatus.COMPLETED.value))
            )
            
            # 添加过滤条件（利用索引）
            filters = [Asset.deleted_at.is_(None)]  # 基础过滤
            
            if status:
                filters.append(Asset.status == status)
            
            if asset_type:
                filters.append(Asset.asset_type == asset_type)
                
            if creator_address:
                filters.append(Asset.creator_address == creator_address)
            
            # 应用过滤条件
            query = query.filter(and_(*filters))
            
            # 优化排序（利用索引）
            query = query.order_by(Asset.created_at.desc())
            
            # 执行分页查询
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 构建结果
            assets_data = []
            for asset in pagination.items:
                # 计算实时统计（使用子查询优化）
                trade_stats = db.session.query(
                    func.count(Trade.id).label('total_trades'),
                    func.sum(Trade.total).label('total_volume')
                ).filter(
                    Trade.asset_id == asset.id,
                    Trade.status == TradeStatus.COMPLETED.value
                ).first()
                
                asset_data = {
                    'id': asset.id,
                    'name': asset.name,
                    'token_symbol': asset.token_symbol,
                    'token_price': float(asset.token_price),
                    'token_supply': asset.token_supply,
                    'remaining_supply': asset.remaining_supply or asset.token_supply,
                    'status': asset.status,
                    'images': asset.images[:1] if asset.images else [],  # 只返回第一张图片
                    'location': asset.location,
                    'created_at': asset.created_at.isoformat() if asset.created_at else None,
                    'total_trades': trade_stats.total_trades or 0,
                    'total_volume': float(trade_stats.total_volume or 0)
                }
                assets_data.append(asset_data)
            
            result = {
                'assets': assets_data,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
            
            # 记录性能
            duration = time.time() - start_time
            self._track_query_performance('get_optimized_asset_list', duration, len(assets_data))
            
            return result
            
        except Exception as e:
            logger.error(f"优化资产列表查询失败: {str(e)}")
            return {'assets': [], 'pagination': {}}
    
    @query_cache(timeout=180)
    def get_optimized_trade_history(self, asset_id: int, page: int = 1, 
                                  per_page: int = 10, trade_type: Optional[str] = None) -> Dict[str, Any]:
        """
        优化的交易历史查询
        
        Args:
            asset_id: 资产ID
            page: 页码
            per_page: 每页数量
            trade_type: 交易类型过滤
            
        Returns:
            Dict: 分页的交易历史数据
        """
        start_time = time.time()
        
        try:
            # 构建优化查询（利用复合索引）
            query = db.session.query(Trade).filter(Trade.asset_id == asset_id)
            
            # 添加类型过滤
            if trade_type:
                query = query.filter(Trade.type == trade_type)
            
            # 优化排序（利用索引）
            query = query.order_by(Trade.created_at.desc())
            
            # 执行分页查询
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 构建结果
            trades_data = []
            for trade in pagination.items:
                trade_data = {
                    'id': trade.id,
                    'type': trade.type,
                    'amount': trade.amount,
                    'price': float(trade.price),
                    'total': float(trade.total),
                    'status': trade.status,
                    'trader_address': trade.trader_address,
                    'tx_hash': trade.tx_hash,
                    'created_at': trade.created_at.isoformat() if trade.created_at else None,
                    'updated_at': trade.status_updated_at.isoformat() if hasattr(trade, 'status_updated_at') and trade.status_updated_at else (trade.created_at.isoformat() if trade.created_at else None)
                }
                trades_data.append(trade_data)
            
            result = {
                'trades': trades_data,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
            
            # 记录性能
            duration = time.time() - start_time
            self._track_query_performance('get_optimized_trade_history', duration, len(trades_data))
            
            return result
            
        except Exception as e:
            logger.error(f"优化交易历史查询失败: {str(e)}")
            return {'trades': [], 'pagination': {}}
    
    @query_cache(timeout=600)
    def get_asset_statistics_batch(self, asset_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        批量获取资产统计信息（减少数据库查询次数）
        
        Args:
            asset_ids: 资产ID列表
            
        Returns:
            Dict: 资产统计信息字典
        """
        start_time = time.time()
        
        try:
            # 使用单个查询获取所有资产的统计信息
            stats_query = db.session.query(
                Trade.asset_id,
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.total).label('total_volume'),
                func.max(Trade.created_at).label('last_trade_at')
            ).filter(
                Trade.asset_id.in_(asset_ids),
                Trade.status == TradeStatus.COMPLETED.value
            ).group_by(Trade.asset_id)
            
            stats_results = stats_query.all()
            
            # 构建结果字典
            statistics = {}
            for stat in stats_results:
                statistics[stat.asset_id] = {
                    'total_trades': stat.total_trades or 0,
                    'total_volume': float(stat.total_volume or 0),
                    'last_trade_at': stat.last_trade_at.isoformat() if stat.last_trade_at else None
                }
            
            # 为没有交易的资产添加默认统计
            for asset_id in asset_ids:
                if asset_id not in statistics:
                    statistics[asset_id] = {
                        'total_trades': 0,
                        'total_volume': 0.0,
                        'last_trade_at': None
                    }
            
            # 记录性能
            duration = time.time() - start_time
            self._track_query_performance('get_asset_statistics_batch', duration, len(asset_ids))
            
            return statistics
            
        except Exception as e:
            logger.error(f"批量获取资产统计失败: {str(e)}")
            return {}
    
    def get_user_trade_summary(self, user_address: str, days: int = 30) -> Dict[str, Any]:
        """
        获取用户交易摘要（优化查询）
        
        Args:
            user_address: 用户地址
            days: 统计天数
            
        Returns:
            Dict: 用户交易摘要
        """
        start_time = time.time()
        
        try:
            # 计算时间范围
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # 使用单个聚合查询获取所有统计信息
            summary_query = db.session.query(
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.total).label('total_volume'),
                func.count(Trade.id).filter(Trade.type == TradeType.BUY.value).label('buy_trades'),
                func.count(Trade.id).filter(Trade.type == TradeType.SELL.value).label('sell_trades'),
                func.sum(Trade.total).filter(Trade.type == TradeType.BUY.value).label('buy_volume'),
                func.sum(Trade.total).filter(Trade.type == TradeType.SELL.value).label('sell_volume')
            ).filter(
                Trade.trader_address == user_address,
                Trade.status == TradeStatus.COMPLETED.value,
                Trade.created_at >= since_date
            )
            
            summary = summary_query.first()
            
            result = {
                'user_address': user_address,
                'period_days': days,
                'total_trades': summary.total_trades or 0,
                'total_volume': float(summary.total_volume or 0),
                'buy_trades': summary.buy_trades or 0,
                'sell_trades': summary.sell_trades or 0,
                'buy_volume': float(summary.buy_volume or 0),
                'sell_volume': float(summary.sell_volume or 0),
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # 记录性能
            duration = time.time() - start_time
            self._track_query_performance('get_user_trade_summary', duration, 1)
            
            return result
            
        except Exception as e:
            logger.error(f"获取用户交易摘要失败: {str(e)}")
            return {}
    
    def execute_optimized_raw_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行优化的原生SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            List: 查询结果
        """
        start_time = time.time()
        
        try:
            # 执行查询
            result = db.session.execute(text(query), params or {})
            
            # 转换结果为字典列表
            columns = result.keys()
            rows = result.fetchall()
            
            data = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # 处理特殊类型
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    elif hasattr(value, '__float__'):
                        value = float(value)
                    row_dict[column] = value
                data.append(row_dict)
            
            # 记录性能
            duration = time.time() - start_time
            self._track_query_performance('execute_optimized_raw_query', duration, len(data))
            
            return data
            
        except Exception as e:
            logger.error(f"执行原生查询失败: {str(e)}")
            return []
    
    def get_query_performance_stats(self) -> Dict[str, Any]:
        """
        获取查询性能统计
        
        Returns:
            Dict: 性能统计信息
        """
        return {
            'query_stats': self.query_stats,
            'total_queries': sum(stats['total_calls'] for stats in self.query_stats.values()),
            'avg_duration_overall': sum(stats['avg_duration'] for stats in self.query_stats.values()) / len(self.query_stats) if self.query_stats else 0,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def clear_query_cache(self, pattern: str = None):
        """
        清除查询缓存
        
        Args:
            pattern: 缓存键模式，如果为None则清除所有查询缓存
        """
        try:
            if self._redis_client:
                if pattern:
                    keys = self._redis_client.keys(f"query_cache:*{pattern}*")
                else:
                    keys = self._redis_client.keys("query_cache:*")
                
                if keys:
                    self._redis_client.delete(*keys)
                    logger.info(f"已清除查询缓存: {len(keys)} 个key")
            
        except Exception as e:
            logger.error(f"清除查询缓存失败: {str(e)}")

# 全局查询优化器实例
query_optimizer = QueryOptimizer()