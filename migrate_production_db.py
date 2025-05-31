#!/usr/bin/env python3
"""
生产环境数据库迁移脚本
"""

import sys
import os
import psycopg2
from psycopg2 import sql

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate_production_db():
    """迁移生产环境数据库"""
    try:
        # 连接生产环境PostgreSQL
        print("🔄 连接生产环境数据库...")
        conn = psycopg2.connect(
            host="localhost",
            database="rwa_hub",
            user="rwa_hub_user",
            password="password",
            sslmode="require"
        )
        
        cursor = conn.cursor()
        print("✅ 数据库连接成功")
        
        # 检查message_type字段是否存在
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'share_messages' AND column_name = 'message_type'
        """)
        
        if cursor.fetchone():
            print("✅ message_type字段已存在，无需迁移")
            conn.close()
            return True
        
        print("🔄 添加message_type字段...")
        
        # 添加message_type字段
        cursor.execute("""
            ALTER TABLE share_messages 
            ADD COLUMN message_type VARCHAR(50) NOT NULL DEFAULT 'share_content'
        """)
        
        # 提交更改
        conn.commit()
        print("✅ 成功添加message_type字段")
        
        # 验证字段添加
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'share_messages' AND column_name = 'message_type'
        """)
        
        if cursor.fetchone():
            print("✅ 字段验证成功")
        else:
            print("❌ 字段验证失败")
            conn.close()
            return False
        
        # 检查现有数据
        cursor.execute("SELECT COUNT(*) FROM share_messages")
        existing_count = cursor.fetchone()[0]
        print(f"📊 现有分享消息数量：{existing_count}")
        
        conn.close()
        print("✅ 数据库迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败：{e}")
        return False

if __name__ == "__main__":
    print("🚀 开始执行生产环境数据库迁移...")
    success = migrate_production_db()
    
    if success:
        print("\n🎉 迁移成功完成！")
        print("📝 现在可以运行初始化脚本：python init_share_messages.py")
    else:
        print("\n💥 迁移失败，请检查错误信息")
        sys.exit(1) 