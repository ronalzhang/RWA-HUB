#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库性能优化索引 - 任务5.3优化数据库查询性能
添加必要的数据库索引以提升查询性能
"""

import logging
from datetime import datetime
from sqlalchemy import text
from app.extensions import db
from flask import current_app

logger = logging.getLogger(__name__)

def add_performance_indexes():
    """
    添加性能优化索引
    """
    try:
        logger.info("开始添加数据库性能优化索引...")
        
        # 索引定义列表
        indexes = [
            # 资产表索引
            {
                'name': 'idx_assets_status_deleted',
                'table': 'assets',
                'columns': ['status', 'deleted_at'],
                'description': '资产状态和删除状态复合索引'
            },
            {
                'name': 'idx_assets_type_status',
                'table': 'assets',
                'columns': ['asset_type', 'status'],
                'description': '资产类型和状态复合索引'
            },
            {
                'name': 'idx_assets_creator_status',
                'table': 'assets',
                'columns': ['creator_address', 'status'],
                'description': '创建者地址和状态复合索引'
            },
            {
                'name': 'idx_assets_created_at',
                'table': 'assets',
                'columns': ['created_at'],
                'description': '资产创建时间索引（用于排序）'
            },
            {
                'name': 'idx_assets_remaining_supply',
                'table': 'assets',
                'columns': ['remaining_supply'],
                'description': '剩余供应量索引（用于可售资产查询）'
            },
            
            # 交易表索引
            {
                'name': 'idx_trades_asset_id_status',
                'table': 'trades',
                'columns': ['asset_id', 'status'],
                'description': '资产ID和交易状态复合索引'
            },
            {
                'name': 'idx_trades_trader_address',
                'table': 'trades',
                'columns': ['trader_address'],
                'description': '交易者地址索引'
            },
            {
                'name': 'idx_trades_created_at',
                'table': 'trades',
                'columns': ['created_at'],
                'description': '交易创建时间索引（用于排序）'
            },
            {
                'name': 'idx_trades_tx_hash',
                'table': 'trades',
                'columns': ['tx_hash'],
                'description': '交易哈希索引（用于查询确认状态）'
            },
            {
                'name': 'idx_trades_type_status',
                'table': 'trades',
                'columns': ['type', 'status'],
                'description': '交易类型和状态复合索引'
            },
            
            # 用户推荐表索引
            {
                'name': 'idx_user_referrals_user_address',
                'table': 'user_referrals',
                'columns': ['user_address'],
                'description': '用户地址索引'
            },
            {
                'name': 'idx_user_referrals_referrer_address',
                'table': 'user_referrals',
                'columns': ['referrer_address'],
                'description': '推荐人地址索引'
            },
            {
                'name': 'idx_user_referrals_status',
                'table': 'user_referrals',
                'columns': ['status'],
                'description': '推荐状态索引'
            },
            
            # 佣金记录表索引
            {
                'name': 'idx_commission_records_referrer',
                'table': 'commission_records',
                'columns': ['referrer_address'],
                'description': '推荐人地址索引'
            },
            {
                'name': 'idx_commission_records_referred',
                'table': 'commission_records',
                'columns': ['referred_address'],
                'description': '被推荐人地址索引'
            },
            {
                'name': 'idx_commission_records_status',
                'table': 'commission_records',
                'columns': ['status'],
                'description': '佣金状态索引'
            },
            {
                'name': 'idx_commission_records_created_at',
                'table': 'commission_records',
                'columns': ['created_at'],
                'description': '佣金创建时间索引'
            },
            
            # 分红记录表索引（如果存在）
            {
                'name': 'idx_dividends_asset_id_status',
                'table': 'dividends',
                'columns': ['asset_id', 'status'],
                'description': '资产ID和分红状态复合索引'
            },
            {
                'name': 'idx_dividends_created_at',
                'table': 'dividends',
                'columns': ['created_at'],
                'description': '分红创建时间索引'
            },
            
            # 短链接表索引
            {
                'name': 'idx_shortlinks_short_code',
                'table': 'shortlinks',
                'columns': ['short_code'],
                'description': '短链接代码索引'
            },
            {
                'name': 'idx_shortlinks_creator_address',
                'table': 'shortlinks',
                'columns': ['creator_address'],
                'description': '短链接创建者地址索引'
            }
        ]
        
        # 创建索引
        created_count = 0
        skipped_count = 0
        
        for index_info in indexes:
            try:
                # 检查索引是否已存在
                check_sql = text(f"""
                    SELECT COUNT(*) as count 
                    FROM pg_indexes 
                    WHERE tablename = :table_name 
                    AND indexname = :index_name
                """)
                
                result = db.session.execute(check_sql, {
                    'table_name': index_info['table'],
                    'index_name': index_info['name']
                }).fetchone()
                
                if result and result.count > 0:
                    logger.info(f"索引已存在，跳过: {index_info['name']}")
                    skipped_count += 1
                    continue
                
                # 检查表是否存在
                table_check_sql = text(f"""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_name = :table_name
                """)
                
                table_result = db.session.execute(table_check_sql, {
                    'table_name': index_info['table']
                }).fetchone()
                
                if not table_result or table_result.count == 0:
                    logger.warning(f"表不存在，跳过索引创建: {index_info['table']}")
                    skipped_count += 1
                    continue
                
                # 创建索引
                columns_str = ', '.join(index_info['columns'])
                create_sql = text(f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_info['name']} 
                    ON {index_info['table']} ({columns_str})
                """)
                
                db.session.execute(create_sql)
                db.session.commit()
                
                logger.info(f"索引创建成功: {index_info['name']} - {index_info['description']}")
                created_count += 1
                
            except Exception as index_error:
                logger.error(f"创建索引失败: {index_info['name']}, 错误: {str(index_error)}")
                db.session.rollback()
                continue
        
        logger.info(f"数据库索引优化完成: 创建 {created_count} 个索引, 跳过 {skipped_count} 个索引")
        
        return {
            'success': True,
            'created_indexes': created_count,
            'skipped_indexes': skipped_count,
            'total_indexes': len(indexes)
        }
        
    except Exception as e:
        logger.error(f"添加数据库索引失败: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }

def analyze_table_statistics():
    """
    分析表统计信息以优化查询计划
    """
    try:
        logger.info("开始分析表统计信息...")
        
        # 需要分析的表列表
        tables = [
            'assets',
            'trades', 
            'user_referrals',
            'commission_records',
            'dividends',
            'shortlinks'
        ]
        
        analyzed_count = 0
        
        for table in tables:
            try:
                # 检查表是否存在
                check_sql = text(f"""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_name = :table_name
                """)
                
                result = db.session.execute(check_sql, {'table_name': table}).fetchone()
                
                if result and result.count > 0:
                    # 分析表
                    analyze_sql = text(f"ANALYZE {table}")
                    db.session.execute(analyze_sql)
                    db.session.commit()
                    
                    logger.info(f"表统计信息分析完成: {table}")
                    analyzed_count += 1
                else:
                    logger.warning(f"表不存在，跳过分析: {table}")
                    
            except Exception as table_error:
                logger.error(f"分析表统计信息失败: {table}, 错误: {str(table_error)}")
                db.session.rollback()
                continue
        
        logger.info(f"表统计信息分析完成: 分析了 {analyzed_count} 个表")
        
        return {
            'success': True,
            'analyzed_tables': analyzed_count
        }
        
    except Exception as e:
        logger.error(f"分析表统计信息失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def optimize_database_performance():
    """
    执行完整的数据库性能优化
    """
    try:
        logger.info("开始执行数据库性能优化...")
        
        # 1. 添加索引
        index_result = add_performance_indexes()
        
        # 2. 分析表统计信息
        analyze_result = analyze_table_statistics()
        
        # 3. 设置数据库连接池参数（如果支持）
        try:
            # 设置一些PostgreSQL性能参数
            performance_settings = [
                "SET shared_preload_libraries = 'pg_stat_statements'",
                "SET track_activity_query_size = 2048",
                "SET log_min_duration_statement = 1000"  # 记录超过1秒的查询
            ]
            
            for setting in performance_settings:
                try:
                    db.session.execute(text(setting))
                    logger.info(f"性能参数设置成功: {setting}")
                except Exception as setting_error:
                    logger.warning(f"性能参数设置失败: {setting}, 错误: {str(setting_error)}")
                    
        except Exception as settings_error:
            logger.warning(f"设置性能参数失败: {str(settings_error)}")
        
        result = {
            'success': True,
            'index_optimization': index_result,
            'table_analysis': analyze_result,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"数据库性能优化完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"数据库性能优化失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    # 可以直接运行此脚本进行数据库优化
    from app import create_app
    
    app = create_app()
    with app.app_context():
        result = optimize_database_performance()
        print(f"数据库优化结果: {result}")