#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库迁移脚本：将地址字段从VARCHAR(42)修改为VARCHAR(64)
用于支持更长的区块链地址，特别是SOL地址
"""

import psycopg2
import logging
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('db_migration')

# 数据库连接参数
DB_PARAMS = {
    'dbname': 'rwa_hub',
    'user': 'rwa_hub_user',
    'password': 'password',
    'host': 'localhost'
}

def alter_address_fields():
    """修改数据库中的地址字段长度"""
    try:
        # 连接到数据库
        logger.info("连接到数据库...")
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # 开始事务
        conn.autocommit = False
        
        # 修改assets表中的地址字段
        logger.info("修改assets表中的地址字段...")
        cursor.execute("ALTER TABLE assets ALTER COLUMN token_address TYPE VARCHAR(64);")
        logger.info("已将assets.token_address从VARCHAR(42)修改为VARCHAR(64)")
        
        cursor.execute("ALTER TABLE assets ALTER COLUMN owner_address TYPE VARCHAR(64);")
        logger.info("已将assets.owner_address从VARCHAR(42)修改为VARCHAR(64)")
        
        cursor.execute("ALTER TABLE assets ALTER COLUMN creator_address TYPE VARCHAR(64);")
        logger.info("已将assets.creator_address从VARCHAR(42)修改为VARCHAR(64)")
        
        # 修改trades表中的地址字段
        logger.info("修改trades表中的地址字段...")
        cursor.execute("ALTER TABLE trades ALTER COLUMN trader_address TYPE VARCHAR(64);")
        logger.info("已将trades.trader_address从VARCHAR(42)修改为VARCHAR(64)")
        
        # 修改users表中的地址字段
        logger.info("修改users表中的地址字段...")
        cursor.execute("ALTER TABLE users ALTER COLUMN eth_address TYPE VARCHAR(64);")
        logger.info("已将users.eth_address从VARCHAR(42)修改为VARCHAR(64)")
        
        # 提交事务
        conn.commit()
        logger.info("所有地址字段已成功修改为VARCHAR(64)")
        
    except Exception as e:
        # 回滚事务
        if conn:
            conn.rollback()
        logger.error(f"迁移失败: {str(e)}")
        raise
    finally:
        # 关闭连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        logger.info("开始执行地址字段长度迁移...")
        alter_address_fields()
        logger.info("迁移完成!")
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {str(e)}")
        sys.exit(1) 