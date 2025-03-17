#!/usr/bin/env python
"""
强制修复数据库脚本
直接通过psycopg2连接执行SQL修改，绕过SQLAlchemy
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys

# 数据库连接信息 - 确保与应用配置一致
DB_CONFIG = {
    'dbname': 'rwa_hub',
    'user': 'rwa_hub_user',
    'password': 'password',
    'host': 'localhost'
}

def force_fix_db():
    """强制修复数据库结构"""
    print("开始强制修复数据库结构...")
    
    # 直接连接PostgreSQL
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 1. 检查当前列长度
        cursor.execute("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'trades' AND column_name = 'trader_address';
        """)
        
        current_length = cursor.fetchone()[0]
        print(f"当前trader_address列长度: {current_length}")
        
        # 2. 执行ALTER TABLE语句增加列长度，强制覆盖
        print("执行强制修改...")
        cursor.execute("""
            ALTER TABLE trades 
            ALTER COLUMN trader_address TYPE VARCHAR(64);
        """)
        
        # 3. 验证修改
        cursor.execute("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'trades' AND column_name = 'trader_address';
        """)
        
        new_length = cursor.fetchone()[0]
        print(f"修改后trader_address列长度: {new_length}")
        
        # 4. 提交更改 (虽然已设置自动提交，但为了确保)
        conn.commit()
        
        # 5. 显示trades表完整结构
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'trades'
            ORDER BY ordinal_position;
        """)
        
        print("\ntrades表结构:")
        print("{:<20} {:<20} {:<10}".format("列名", "数据类型", "最大长度"))
        print("-" * 50)
        
        for row in cursor.fetchall():
            column_name = row[0]
            data_type = row[1]
            max_length = row[2] if row[2] is not None else "N/A"
            print("{:<20} {:<20} {:<10}".format(column_name, data_type, max_length))
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        print("\n数据库修复完成!")
        
    except Exception as e:
        print(f"修复过程中出错: {e}")
        return False
    
    return True

if __name__ == "__main__":
    force_fix_db() 