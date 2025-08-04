#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库优化服务
实现数据库连接池优化、查询优化和索引管理
"""

import logging
import time
from typing import Dict, List, Any, Optional
from functools import wraps
from contextlib import contextmanager
from sqlalchemy import text, inspect
from sqlalchemy.pool import QueuePool
from flask import current_app
from app.extensions import db

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self):
        self.slow_query_threshold = 1.0  # 慢查询阈值（秒）
        self.query_stats = {}
        
    def optimize_connection_pool(self, app):
        """优化数据库连接池"""
        try:
            # 配置连接池参数
            pool_settings = {
                'poolclass': QueuePool,
                'pool_size': 20,          # 连接池大小
                'max_overflow': 30,       # 最大溢出连接数
                'pool_timeout': 30,       # 获取连接超时时间
                'pool_recycle': 3600,     # 连接回收时间（1小时）
                'pool_pre_ping': True,    # 连接前ping检查
            }
            
            # 更新数据库URI以包含连接池参数
            if hasattr(app.config, 'SQLALCHEMY_ENGINE_OPTIONS'):
                app.config['SQLALCHEMY_ENGINE_OPTIONS'].update(pool_settings)
            else:
                app.config['SQLALCHEMY_ENGINE_OPTIONS'] = pool_settings
            
            logger.info("数据库连接池优化完成")
            
        except Exception as e:
            logger.error(f"数据库连接池优化失败: {e}")
    
    def create_performance_indexes(self):
        """创建性能优化索引"""
        indexes = [
            # 资产表索引
            "CREATE INDEX IF NOT EXISTS idx_assets_status_deleted ON assets(status, deleted_at) WHERE deleted_at IS NULL;",
            "CREATE INDEX IF NOT EXISTS idx_assets_creator_status ON assets(creator_address, status);",
            "CREATE INDEX IF NOT EXISTS idx_assets_type_status ON assets(asset_type, status);",
            "CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);",
            
            # 交易表索引
            "CREATE INDEX IF NOT EXISTS idx_trades_asset_id ON trades(asset_id);",
            "CREATE INDEX IF NOT EXISTS idx_trades_trader_address ON trades(trader_address);",
            "CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);",
            
            # 用户表索引
            "CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address);",
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);",
            
            # 佣金表索引
            "CREATE INDEX IF NOT EXISTS idx_commissions_referrer ON commissions(referrer_address);",
            "CREATE INDEX IF NOT EXISTS idx_commissions_referred ON commissions(referred_address);",
            "CREATE INDEX IF NOT EXISTS idx_commissions_created_at ON commissions(created_at DESC);",
            
            # 推荐关系表索引
            "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON user_referrals(referrer_address);",
            "CREATE INDEX IF NOT EXISTS idx_referrals_user ON user_referrals(user_address);",
            
            # 管理员表索引
            "CREATE INDEX IF NOT EXISTS idx_admin_users_wallet ON admin_users(wallet_address);",
        ]
        
        try:
            for index_sql in indexes:
                db.session.execute(text(index_sql))
            
            db.session.commit()
            logger.info(f"创建了 {len(indexes)} 个性能索引")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建性能索引失败: {e}")
    
    def analyze_table_statistics(self) -> Dict[str, Any]:
        """分析表统计信息"""
        try:
            stats = {}
            
            # 获取所有表的统计信息
            tables_query = """
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables 
                ORDER BY n_live_tup DESC;
            """
            
            result = db.session.execute(text(tables_query))
            
            for row in result:
                table_name = row.tablename
                stats[table_name] = {
                    'schema': row.schemaname,
                    'inserts': row.inserts or 0,
                    'updates': row.updates or 0,
                    'deletes': row.deletes or 0,
                    'live_tuples': row.live_tuples or 0,
                    'dead_tuples': row.dead_tuples or 0,
                    'last_vacuum': row.last_vacuum,
                    'last_autovacuum': row.last_autovacuum,
                    'last_analyze': row.last_analyze,
                    'last_autoanalyze': row.last_autoanalyze
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"分析表统计信息失败: {e}")
            return {}
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取慢查询信息"""
        try:
            # 需要启用 pg_stat_statements 扩展
            slow_queries_sql = """
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements 
                WHERE mean_time > %s
                ORDER BY mean_time DESC 
                LIMIT %s;
            """
            
            result = db.session.execute(
                text(slow_queries_sql), 
                (self.slow_query_threshold * 1000, limit)  # 转换为毫秒
            )
            
            slow_queries = []
            for row in result:
                slow_queries.append({
                    'query': row.query[:200] + '...' if len(row.query) > 200 else row.query,
                    'calls': row.calls,
                    'total_time': row.total_time,
                    'mean_time': row.mean_time,
                    'rows': row.rows,
                    'hit_percent': row.hit_percent or 0
                })
            
            return slow_queries
            
        except Exception as e:
            logger.warning(f"获取慢查询信息失败（可能需要启用pg_stat_statements）: {e}")
            return []
    
    def optimize_table_maintenance(self):
        """执行表维护操作"""
        try:
            # 获取需要维护的表
            maintenance_query = """
                SELECT 
                    schemaname,
                    tablename,
                    n_dead_tup,
                    n_live_tup,
                    CASE 
                        WHEN n_live_tup > 0 
                        THEN n_dead_tup::float / n_live_tup::float 
                        ELSE 0 
                    END as dead_ratio
                FROM pg_stat_user_tables 
                WHERE n_dead_tup > 1000 
                   OR (n_live_tup > 0 AND n_dead_tup::float / n_live_tup::float > 0.1)
                ORDER BY dead_ratio DESC;
            """
            
            result = db.session.execute(text(maintenance_query))
            tables_to_maintain = []
            
            for row in result:
                tables_to_maintain.append({
                    'schema': row.schemaname,
                    'table': row.tablename,
                    'dead_tuples': row.n_dead_tup,
                    'live_tuples': row.n_live_tup,
                    'dead_ratio': row.dead_ratio
                })
            
            # 执行VACUUM ANALYZE
            for table_info in tables_to_maintain:
                table_name = table_info['table']
                try:
                    # 注意：VACUUM不能在事务中执行
                    db.session.commit()  # 提交当前事务
                    
                    # 执行ANALYZE（可以在事务中执行）
                    db.session.execute(text(f"ANALYZE {table_name};"))
                    db.session.commit()
                    
                    logger.info(f"已对表 {table_name} 执行ANALYZE")
                    
                except Exception as e:
                    logger.error(f"维护表 {table_name} 失败: {e}")
                    db.session.rollback()
            
            return tables_to_maintain
            
        except Exception as e:
            logger.error(f"表维护操作失败: {e}")
            db.session.rollback()
            return []
    
    def get_database_size_info(self) -> Dict[str, Any]:
        """获取数据库大小信息"""
        try:
            # 数据库总大小
            db_size_query = """
                SELECT pg_size_pretty(pg_database_size(current_database())) as database_size;
            """
            
            # 各表大小
            table_sizes_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """
            
            # 获取数据库大小
            db_size_result = db.session.execute(text(db_size_query)).fetchone()
            database_size = db_size_result.database_size if db_size_result else "Unknown"
            
            # 获取表大小
            table_sizes = []
            table_result = db.session.execute(text(table_sizes_query))
            
            for row in table_result:
                table_sizes.append({
                    'schema': row.schemaname,
                    'table': row.tablename,
                    'size': row.size,
                    'size_bytes': row.size_bytes
                })
            
            return {
                'database_size': database_size,
                'table_sizes': table_sizes
            }
            
        except Exception as e:
            logger.error(f"获取数据库大小信息失败: {e}")
            return {}
    
    def monitor_connection_pool(self) -> Dict[str, Any]:
        """监控连接池状态"""
        try:
            engine = db.engine
            pool = engine.pool
            
            return {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid()
            }
            
        except Exception as e:
            logger.error(f"监控连接池失败: {e}")
            return {}

def monitor_query_performance(operation_name: str = ''):
    """查询性能监控装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or f.__name__
            
            try:
                result = f(*args, **kwargs)
                return result
                
            except Exception as e:
                # 记录查询错误
                from app.services.application_monitor import get_monitor
                get_monitor().track_error('DATABASE_QUERY_ERROR', str(e), {
                    'operation': operation,
                    'function': f.__name__
                })
                raise
                
            finally:
                duration = time.time() - start_time
                
                # 记录查询性能
                from app.services.application_monitor import get_monitor
                get_monitor().track_database_performance(
                    query_type=operation,
                    duration=duration,
                    table_name=operation_name
                )
                
                # 记录慢查询
                if duration > 1.0:
                    logger.warning(f"慢查询检测: {operation}, 耗时: {duration:.2f}s")
        
        return decorated_function
    return decorator

@contextmanager
def database_transaction():
    """数据库事务上下文管理器"""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"数据库事务失败: {e}")
        raise
    finally:
        db.session.close()

# 全局数据库优化器实例
_db_optimizer_instance = None

def get_database_optimizer() -> DatabaseOptimizer:
    """获取全局数据库优化器实例"""
    global _db_optimizer_instance
    if _db_optimizer_instance is None:
        _db_optimizer_instance = DatabaseOptimizer()
    return _db_optimizer_instance