#!/usr/bin/env python3
"""
检查佣金相关表数据的脚本
"""
from app import create_app
from app.models import db

def main():
    app = create_app()
    with app.app_context():
        print("=== 检查佣金相关表数据 ===")
        
        tables = [
            'commission_records', 
            'commission_settings', 
            'commissions', 
            'distribution_levels', 
            'user_referrals', 
            'users'
        ]
        
        for table in tables:
            try:
                result = db.session.execute(db.text(f'SELECT COUNT(*) FROM {table}'))
                count = result.scalar()
                print(f'{table}: {count} 条记录')
                
                if count > 0 and count < 10:
                    result = db.session.execute(db.text(f'SELECT * FROM {table} LIMIT 5'))
                    rows = result.fetchall()
                    print(f'  样本数据:')
                    for row in rows:
                        print(f'    {dict(row._mapping)}')
                elif count > 0:
                    result = db.session.execute(db.text(f'SELECT * FROM {table} LIMIT 3'))
                    rows = result.fetchall()
                    print(f'  前3条数据:')
                    for row in rows:
                        print(f'    {dict(row._mapping)}')
                        
            except Exception as e:
                print(f'{table}: 查询失败 - {e}')
        
        print("\n=== 检查用户表结构 ===")
        try:
            result = db.session.execute(db.text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            print("users表字段:")
            for col in columns:
                print(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        except Exception as e:
            print(f"查询users表结构失败: {e}")

if __name__ == '__main__':
    main() 