#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建AssetStatusHistory表的脚本
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# 数据库连接信息
db_params = {
    'dbname': 'rwa_hub',
    'user': 'rwa_hub_user',
    'password': 'password',
    'host': 'localhost'
}

def main():
    # 连接到数据库
    conn = psycopg2.connect(**db_params)
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'asset_status_history')")
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("表 asset_status_history 已存在，无需创建")
        else:
            # 创建表
            print("创建表 asset_status_history...")
            cursor.execute("""
                CREATE TABLE asset_status_history (
                    id SERIAL PRIMARY KEY,
                    asset_id INTEGER NOT NULL,
                    old_status INTEGER NOT NULL,
                    new_status INTEGER NOT NULL,
                    change_time TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                    change_reason VARCHAR(512)
                )
            """)
            print("表 asset_status_history 创建成功")
            
    except Exception as e:
        print(f"创建表时出错: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main() 