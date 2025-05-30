#!/usr/bin/env python3
"""
创建IP访问记录表的数据库迁移
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import IPVisit
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ip_visits_table():
    """创建IP访问记录表"""
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("开始创建IP访问记录表...")
            
            # 创建表
            db.create_all()
            
            logger.info("✅ IP访问记录表创建成功！")
            
            # 验证表是否创建成功
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'ip_visits' in tables:
                logger.info("✅ 验证：ip_visits表已存在于数据库中")
                
                # 显示表结构
                columns = inspector.get_columns('ip_visits')
                logger.info("📊 表结构：")
                for column in columns:
                    logger.info(f"   - {column['name']}: {column['type']}")
                
                # 显示索引
                indexes = inspector.get_indexes('ip_visits')
                if indexes:
                    logger.info("📊 索引：")
                    for index in indexes:
                        logger.info(f"   - {index['name']}: {index['column_names']}")
            else:
                logger.error("❌ 表创建失败：ip_visits表不存在")
                
        except Exception as e:
            logger.error(f"❌ 创建IP访问记录表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    create_ip_visits_table() 