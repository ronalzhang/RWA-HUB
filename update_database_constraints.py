#!/usr/bin/env python3
"""
更新数据库约束以支持新的资产状态
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def main():
    app = create_app()
    with app.app_context():
        print("=== 更新数据库约束 ===\n")
        
        try:
            # 更新状态约束以支持状态8 (PAYMENT_PROCESSING)
            print("1. 删除旧的状态约束...")
            db.session.execute(text("ALTER TABLE assets DROP CONSTRAINT IF EXISTS ck_status_valid"))
            
            print("2. 添加新的状态约束...")
            db.session.execute(text("ALTER TABLE assets ADD CONSTRAINT ck_status_valid CHECK (status IN (1, 2, 3, 4, 5, 6, 7, 8))"))
            
            db.session.commit()
            print("✓ 数据库约束更新成功")
            
            # 验证约束
            print("\n3. 验证约束...")
            result = db.session.execute(text("""
                SELECT constraint_name, check_clause 
                FROM information_schema.check_constraints 
                WHERE constraint_name = 'ck_status_valid'
            """))
            
            for row in result:
                print(f"约束名称: {row[0]}")
                print(f"约束条件: {row[1]}")
            
            print("\n=== 约束更新完成 ===")
            
        except Exception as e:
            print(f"✗ 更新失败: {e}")
            db.session.rollback()

if __name__ == "__main__":
    main() 