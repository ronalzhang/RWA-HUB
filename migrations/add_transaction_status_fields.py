#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库迁移脚本 - 添加交易状态管理字段
实现任务3.3优化交易状态管理的数据库结构更新
"""

import logging
from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

def upgrade_trades_table():
    """升级trades表结构"""
    try:
        logger.info("开始升级trades表结构...")
        
        # 检查字段是否已存在
        check_columns_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'trades' 
        AND column_name IN ('error_message', 'confirmation_count', 'estimated_completion_time', 
                           'status_updated_at', 'retry_count', 'blockchain_network');
        """
        
        result = db.session.execute(text(check_columns_sql))
        existing_columns = [row[0] for row in result.fetchall()]
        
        # 需要添加的字段
        new_columns = {
            'error_message': 'TEXT',
            'confirmation_count': 'INTEGER DEFAULT 0',
            'estimated_completion_time': 'TIMESTAMP',
            'status_updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'retry_count': 'INTEGER DEFAULT 0',
            'blockchain_network': "VARCHAR(20) DEFAULT 'solana'"
        }
        
        # 添加不存在的字段
        for column_name, column_definition in new_columns.items():
            if column_name not in existing_columns:
                alter_sql = f"ALTER TABLE trades ADD COLUMN {column_name} {column_definition};"
                logger.info(f"添加字段: {column_name}")
                db.session.execute(text(alter_sql))
            else:
                logger.info(f"字段已存在，跳过: {column_name}")
        
        # 更新现有记录的status_updated_at字段
        update_sql = """
        UPDATE trades 
        SET status_updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
        WHERE status_updated_at IS NULL;
        """
        db.session.execute(text(update_sql))
        
        # 提交更改
        db.session.commit()
        
        logger.info("trades表结构升级完成")
        return True
        
    except Exception as e:
        logger.error(f"升级trades表结构失败: {str(e)}")
        db.session.rollback()
        return False

def create_transaction_status_history_table():
    """创建交易状态历史表"""
    try:
        logger.info("创建交易状态历史表...")
        
        # 检查表是否已存在
        check_table_sql = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'transaction_status_history';
        """
        
        result = db.session.execute(text(check_table_sql))
        if result.fetchone():
            logger.info("交易状态历史表已存在，跳过创建")
            return True
        
        # 创建表
        create_table_sql = """
        CREATE TABLE transaction_status_history (
            id SERIAL PRIMARY KEY,
            trade_id INTEGER NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
            from_status VARCHAR(50),
            to_status VARCHAR(50) NOT NULL,
            changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            change_reason TEXT,
            context_data TEXT,
            created_by VARCHAR(100),
            INDEX idx_trade_id (trade_id),
            INDEX idx_changed_at (changed_at),
            INDEX idx_to_status (to_status)
        );
        """
        
        db.session.execute(text(create_table_sql))
        db.session.commit()
        
        logger.info("交易状态历史表创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建交易状态历史表失败: {str(e)}")
        db.session.rollback()
        return False

def create_transaction_metrics_table():
    """创建交易指标表"""
    try:
        logger.info("创建交易指标表...")
        
        # 检查表是否已存在
        check_table_sql = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'transaction_metrics';
        """
        
        result = db.session.execute(text(check_table_sql))
        if result.fetchone():
            logger.info("交易指标表已存在，跳过创建")
            return True
        
        # 创建表
        create_table_sql = """
        CREATE TABLE transaction_metrics (
            id SERIAL PRIMARY KEY,
            trade_id INTEGER NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
            metric_name VARCHAR(100) NOT NULL,
            metric_value DECIMAL(20,6),
            metric_text TEXT,
            recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_trade_id (trade_id),
            INDEX idx_metric_name (metric_name),
            INDEX idx_recorded_at (recorded_at),
            UNIQUE KEY unique_trade_metric (trade_id, metric_name)
        );
        """
        
        db.session.execute(text(create_table_sql))
        db.session.commit()
        
        logger.info("交易指标表创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建交易指标表失败: {str(e)}")
        db.session.rollback()
        return False

def add_indexes_for_performance():
    """添加性能优化索引"""
    try:
        logger.info("添加性能优化索引...")
        
        # 需要添加的索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_trades_status_updated ON trades(status, status_updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_trades_confirmation_count ON trades(confirmation_count);",
            "CREATE INDEX IF NOT EXISTS idx_trades_blockchain_network ON trades(blockchain_network);",
            "CREATE INDEX IF NOT EXISTS idx_trades_retry_count ON trades(retry_count);",
            "CREATE INDEX IF NOT EXISTS idx_trades_estimated_completion ON trades(estimated_completion_time);",
            "CREATE INDEX IF NOT EXISTS idx_trades_active_status ON trades(status) WHERE status IN ('pending', 'pending_payment', 'pending_confirmation', 'processing');"
        ]
        
        for index_sql in indexes:
            try:
                db.session.execute(text(index_sql))
                logger.info(f"索引创建成功: {index_sql[:50]}...")
            except Exception as index_error:
                logger.warning(f"索引创建失败: {str(index_error)}")
        
        db.session.commit()
        
        logger.info("性能优化索引添加完成")
        return True
        
    except Exception as e:
        logger.error(f"添加性能优化索引失败: {str(e)}")
        db.session.rollback()
        return False

def migrate_existing_trade_statuses():
    """迁移现有交易状态"""
    try:
        logger.info("迁移现有交易状态...")
        
        # 统计现有状态
        status_count_sql = """
        SELECT status, COUNT(*) as count 
        FROM trades 
        GROUP BY status;
        """
        
        result = db.session.execute(text(status_count_sql))
        status_counts = dict(result.fetchall())
        
        logger.info(f"现有交易状态统计: {status_counts}")
        
        # 更新无效状态（如果有的话）
        # 这里可以根据实际情况添加状态迁移逻辑
        
        # 为现有交易创建初始状态历史记录
        create_initial_history_sql = """
        INSERT INTO transaction_status_history (trade_id, from_status, to_status, changed_at, change_reason)
        SELECT 
            id as trade_id,
            NULL as from_status,
            status as to_status,
            COALESCE(status_updated_at, created_at, CURRENT_TIMESTAMP) as changed_at,
            'Initial status from migration' as change_reason
        FROM trades 
        WHERE id NOT IN (
            SELECT DISTINCT trade_id FROM transaction_status_history
        );
        """
        
        try:
            db.session.execute(text(create_initial_history_sql))
            db.session.commit()
            logger.info("初始状态历史记录创建完成")
        except Exception as history_error:
            logger.warning(f"创建初始状态历史记录失败: {str(history_error)}")
        
        logger.info("现有交易状态迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"迁移现有交易状态失败: {str(e)}")
        return False

def main():
    """主迁移函数"""
    app = create_app()
    
    with app.app_context():
        logger.info("开始交易状态管理数据库迁移...")
        
        success_count = 0
        total_steps = 5
        
        # 1. 升级trades表结构
        if upgrade_trades_table():
            success_count += 1
            logger.info("✅ 步骤1/5: trades表结构升级完成")
        else:
            logger.error("❌ 步骤1/5: trades表结构升级失败")
        
        # 2. 创建交易状态历史表
        if create_transaction_status_history_table():
            success_count += 1
            logger.info("✅ 步骤2/5: 交易状态历史表创建完成")
        else:
            logger.error("❌ 步骤2/5: 交易状态历史表创建失败")
        
        # 3. 创建交易指标表
        if create_transaction_metrics_table():
            success_count += 1
            logger.info("✅ 步骤3/5: 交易指标表创建完成")
        else:
            logger.error("❌ 步骤3/5: 交易指标表创建失败")
        
        # 4. 添加性能优化索引
        if add_indexes_for_performance():
            success_count += 1
            logger.info("✅ 步骤4/5: 性能优化索引添加完成")
        else:
            logger.error("❌ 步骤4/5: 性能优化索引添加失败")
        
        # 5. 迁移现有交易状态
        if migrate_existing_trade_statuses():
            success_count += 1
            logger.info("✅ 步骤5/5: 现有交易状态迁移完成")
        else:
            logger.error("❌ 步骤5/5: 现有交易状态迁移失败")
        
        # 总结
        if success_count == total_steps:
            logger.info(f"🎉 交易状态管理数据库迁移完成！成功执行 {success_count}/{total_steps} 个步骤")
            return True
        else:
            logger.warning(f"⚠️ 交易状态管理数据库迁移部分完成，成功执行 {success_count}/{total_steps} 个步骤")
            return False

if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = main()
    exit(0 if success else 1)