#!/usr/bin/env python
import sys
import os
import logging

# 将项目根目录添加到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app import create_app, db
from sqlalchemy import text, exc

def run_migration():
    """运行迁移脚本，添加新字段到trades表"""
    logger.info("开始执行迁移脚本...")
    
    app = create_app()
    with app.app_context():
        # 每个字段单独处理，避免一个失败影响其他字段
        add_column(db, 'total', 'FLOAT')
        add_column(db, 'fee', 'FLOAT')
        add_column(db, 'fee_rate', 'FLOAT')
        
        logger.info("迁移脚本执行完成")
        return True

def add_column(db, column_name, column_type):
    """添加单个列到表中"""
    conn = db.engine.connect()
    trans = conn.begin()
    
    try:
        # 检查字段是否存在
        try:
            conn.execute(text(f"SELECT {column_name} FROM trades LIMIT 1"))
            logger.info(f"字段 '{column_name}' 已存在，跳过创建")
            trans.rollback()  # 不需要进行任何更改
            return True
        except exc.ProgrammingError:
            # 字段不存在，开始新事务添加字段
            trans.rollback()
            
            # 创建新事务
            trans = conn.begin()
            logger.info(f"字段 '{column_name}' 不存在，将创建")
            conn.execute(text(f"ALTER TABLE trades ADD COLUMN {column_name} {column_type}"))
            trans.commit()
            logger.info(f"字段 '{column_name}' 已创建")
            return True
    except Exception as e:
        if trans.is_active:
            trans.rollback()
        logger.error(f"添加字段 '{column_name}' 失败：{str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("数据库迁移完成")
        sys.exit(0)
    else:
        print("数据库迁移失败")
        sys.exit(1) 