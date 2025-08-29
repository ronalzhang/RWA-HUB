#!/usr/bin/env python3
"""
添加holdings表的status字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def add_holdings_status_field():
    """添加holdings表的status字段"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查status字段是否已存在
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'holdings' AND column_name = 'status'
            """))
            
            if result.fetchone():
                print("✓ holdings.status字段已存在，跳过添加")
                return True
            
            # 添加status字段
            print("正在添加holdings.status字段...")
            db.session.execute(text("""
                ALTER TABLE holdings 
                ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL
            """))
            
            db.session.commit()
            print("✓ 成功添加holdings.status字段")
            return True
            
        except Exception as e:
            print(f"✗ 添加holdings.status字段失败: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = add_holdings_status_field()
    sys.exit(0 if success else 1)