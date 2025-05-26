#!/usr/bin/env python3
"""
为User表添加分销商相关字段
"""
from app import create_app
from app.models import db

def add_distributor_fields():
    """为User表添加分销商相关字段"""
    print("=== 为User表添加分销商相关字段 ===")
    
    try:
        # 检查字段是否已存在
        result = db.session.execute(db.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN ('is_distributor', 'is_verified', 'is_blocked', 'referrer_address')
        """))
        existing_columns = [row[0] for row in result.fetchall()]
        print(f"已存在的字段: {existing_columns}")
        
        # 添加缺失的字段
        fields_to_add = [
            ('is_distributor', 'BOOLEAN DEFAULT FALSE', '是否为分销商'),
            ('is_verified', 'BOOLEAN DEFAULT FALSE', '是否已认证'),
            ('is_blocked', 'BOOLEAN DEFAULT FALSE', '是否被冻结'),
            ('referrer_address', 'VARCHAR(64)', '推荐人地址')
        ]
        
        for field_name, field_type, description in fields_to_add:
            if field_name not in existing_columns:
                sql = f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"
                db.session.execute(db.text(sql))
                print(f"添加字段: {field_name} ({description})")
            else:
                print(f"字段已存在: {field_name}")
        
        db.session.commit()
        print("字段添加完成！")
        
    except Exception as e:
        print(f"添加字段失败: {e}")
        db.session.rollback()

def main():
    """主函数"""
    app = create_app()
    with app.app_context():
        add_distributor_fields()

if __name__ == '__main__':
    main() 