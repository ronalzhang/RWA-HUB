#!/usr/bin/env python3
"""
数据库迁移脚本：为share_messages表添加message_type字段
"""

import sys
import sqlite3
from pathlib import Path

def migrate_database():
    """执行数据库迁移"""
    try:
        # 连接数据库
        db_path = Path("instance/app.db")
        if not db_path.exists():
            print("❌ 数据库文件不存在，请先运行应用程序创建数据库")
            return False
            
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='share_messages'")
        if not cursor.fetchone():
            print("❌ share_messages表不存在")
            conn.close()
            return False
            
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(share_messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'message_type' in columns:
            print("✅ message_type字段已存在，无需迁移")
            conn.close()
            return True
            
        print("🔄 开始迁移数据库...")
        
        # 添加message_type字段
        cursor.execute("""
            ALTER TABLE share_messages 
            ADD COLUMN message_type VARCHAR(50) NOT NULL DEFAULT 'share_content'
        """)
        
        # 提交更改
        conn.commit()
        print("✅ 成功添加message_type字段")
        
        # 验证字段添加
        cursor.execute("PRAGMA table_info(share_messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'message_type' in columns:
            print("✅ 字段验证成功")
        else:
            print("❌ 字段验证失败")
            conn.close()
            return False
            
        conn.close()
        print("✅ 数据库迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始执行share_messages表迁移...")
    success = migrate_database()
    
    if success:
        print("\n🎉 迁移成功完成！")
        print("📝 现在您可以：")
        print("   1. 启动应用程序")
        print("   2. 访问后台管理 -> 分享消息管理")
        print("   3. 添加奖励计划类型的文案")
    else:
        print("\n💥 迁移失败，请检查错误信息")
        sys.exit(1) 