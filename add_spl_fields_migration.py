#!/usr/bin/env python3
"""
添加SPL Token字段到assets表
"""

import sys
from sqlalchemy import text

def main():
    try:
        from app import create_app
        from app.extensions import db

        app = create_app('production')
        with app.app_context():
            print("=== 添加SPL Token字段到assets表 ===")

            # 检查表结构
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'assets'
                AND column_name LIKE '%spl%'
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            print(f"现有SPL相关字段: {existing_columns}")

            # 需要添加的字段
            fields_to_add = [
                ("spl_mint_address", "VARCHAR(44)"),
                ("mint_authority_keypair", "TEXT"),
                ("freeze_authority_keypair", "TEXT"),
                ("metadata_uri", "VARCHAR(500)"),
                ("spl_creation_status", "INTEGER DEFAULT 0"),
                ("spl_creation_tx_hash", "VARCHAR(128)"),
                ("spl_created_at", "TIMESTAMP")
            ]

            added_count = 0
            for field_name, field_type in fields_to_add:
                if field_name not in existing_columns:
                    try:
                        sql = f"ALTER TABLE assets ADD COLUMN {field_name} {field_type}"
                        print(f"执行: {sql}")
                        db.session.execute(text(sql))
                        added_count += 1
                        print(f"✅ 字段 {field_name} 添加成功")
                    except Exception as e:
                        print(f"❌ 字段 {field_name} 添加失败: {e}")
                else:
                    print(f"⚠️ 字段 {field_name} 已存在，跳过")

            if added_count > 0:
                db.session.commit()
                print(f"✅ 成功添加了 {added_count} 个字段")
            else:
                print("ℹ️ 所有字段都已存在，无需添加")

            # 验证字段是否添加成功
            result = db.session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'assets'
                AND column_name LIKE '%spl%'
                ORDER BY column_name
            """))

            print("\n最终的SPL相关字段:")
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]}")

            return True

    except Exception as e:
        print(f"数据库迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)