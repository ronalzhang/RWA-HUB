#!/usr/bin/env python3
"""
重新设计佣金系统
实现简化的35%分佣规则：
- 每个用户只有一个上级和多个下级
- 所有下级给上级分35%佣金
- 包括：本级用户的直接支付金额 + 本级用户的下级上贡上来的佣金总额
"""
from app import create_app
from app.models import db
from datetime import datetime

def redesign_commission_tables():
    """重新设计佣金相关表结构"""
    print("=== 重新设计佣金系统表结构 ===")
    
    try:
        # 1. 清理旧的复杂分销等级设置
        db.session.execute(db.text("DELETE FROM distribution_levels"))
        print("清理旧的分销等级设置")
        
        # 2. 重新设计commission_settings表，简化为35%固定佣金
        db.session.execute(db.text("DELETE FROM commission_settings"))
        
        # 插入新的简化佣金设置
        new_settings = [
            {
                'asset_type_id': None,  # 全局设置
                'commission_rate': 35.0,  # 35%
                'min_amount': 0.01,
                'max_amount': 999999999.0,
                'is_active': True,
                'created_by': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
                'description': '全局35%上级分佣设置'
            }
        ]
        
        for setting in new_settings:
            db.session.execute(db.text("""
                INSERT INTO commission_settings 
                (asset_type_id, commission_rate, min_amount, max_amount, is_active, created_by, created_at, updated_at)
                VALUES (:asset_type_id, :commission_rate, :min_amount, :max_amount, :is_active, :created_by, NOW(), NOW())
            """), setting)
            print(f"添加新佣金设置: {setting['description']}")
        
        # 3. 建立用户推荐关系
        print("\n=== 建立示例推荐关系 ===")
        
        # 设置推荐关系：test_user_1 和 test_user_2 的上级都是 admin_user
        referral_relations = [
            {
                'user_address': '0x1234567890123456789012345678901234567890',
                'referrer_address': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b'
            },
            {
                'user_address': '0x2345678901234567890123456789012345678901',
                'referrer_address': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b'
            }
        ]
        
        for relation in referral_relations:
            # 更新用户的推荐人地址
            db.session.execute(db.text("""
                UPDATE users SET referrer_address = :referrer_address 
                WHERE eth_address = :user_address
            """), relation)
            print(f"设置推荐关系: {relation['user_address']} -> {relation['referrer_address']}")
        
        db.session.commit()
        print("\n佣金系统重新设计完成！")
        
    except Exception as e:
        print(f"重新设计失败: {e}")
        db.session.rollback()

def create_sample_commission_data():
    """创建示例佣金数据，展示35%分佣逻辑"""
    print("\n=== 创建示例佣金数据 ===")
    
    try:
        # 清理旧的佣金记录
        db.session.execute(db.text("DELETE FROM commission_records"))
        
        # 创建示例佣金记录
        sample_records = [
            # 场景1：test_user_1 直接支付100 USDC，admin_user获得35 USDC佣金
            {
                'transaction_id': 'direct_payment_001',
                'asset_id': 1,
                'payer_address': '0x1234567890123456789012345678901234567890',
                'recipient_address': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
                'amount': 35.0,
                'currency': 'USDC',
                'commission_type': 'referral_commission',
                'source_amount': 100.0,
                'commission_rate': 35.0,
                'status': 'paid',
                'description': 'test_user_1直接支付100 USDC的35%佣金'
            },
            # 场景2：test_user_2 直接支付200 USDC，admin_user获得70 USDC佣金
            {
                'transaction_id': 'direct_payment_002',
                'asset_id': 2,
                'payer_address': '0x2345678901234567890123456789012345678901',
                'recipient_address': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
                'amount': 70.0,
                'currency': 'USDC',
                'commission_type': 'referral_commission',
                'source_amount': 200.0,
                'commission_rate': 35.0,
                'status': 'paid',
                'description': 'test_user_2直接支付200 USDC的35%佣金'
            },
            # 场景3：假设test_user_1有下级用户，下级上贡了50 USDC，test_user_1再给admin_user分35%
            {
                'transaction_id': 'upstream_commission_001',
                'asset_id': 3,
                'payer_address': '0x1234567890123456789012345678901234567890',
                'recipient_address': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
                'amount': 17.5,
                'currency': 'USDC',
                'commission_type': 'upstream_commission',
                'source_amount': 50.0,
                'commission_rate': 35.0,
                'status': 'pending',
                'description': 'test_user_1的下级上贡50 USDC，再分35%给admin_user'
            }
        ]
        
        for record in sample_records:
            db.session.execute(db.text("""
                INSERT INTO commission_records 
                (transaction_id, asset_id, payer_address, recipient_address, amount, currency, 
                 commission_type, source_amount, commission_rate, status, description, created_at, updated_at)
                VALUES (:transaction_id, :asset_id, :payer_address, :recipient_address, :amount, :currency,
                        :commission_type, :source_amount, :commission_rate, :status, :description, NOW(), NOW())
            """), record)
            print(f"添加佣金记录: {record['description']} - {record['amount']} USDC")
        
        db.session.commit()
        print("示例佣金数据创建完成！")
        
    except Exception as e:
        print(f"创建示例数据失败: {e}")
        db.session.rollback()

def update_commission_table_structure():
    """更新commission_records表结构，添加新字段"""
    print("\n=== 更新commission_records表结构 ===")
    
    try:
        # 检查并添加新字段
        new_fields = [
            ('payer_address', 'VARCHAR(64)', '支付方地址'),
            ('source_amount', 'DECIMAL(20,8)', '原始金额'),
            ('commission_rate', 'DECIMAL(5,2)', '佣金比例'),
            ('description', 'TEXT', '描述信息')
        ]
        
        for field_name, field_type, description in new_fields:
            try:
                db.session.execute(db.text(f"""
                    ALTER TABLE commission_records ADD COLUMN {field_name} {field_type}
                """))
                print(f"添加字段: {field_name} ({description})")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    print(f"字段已存在: {field_name}")
                else:
                    print(f"添加字段 {field_name} 失败: {e}")
        
        db.session.commit()
        print("表结构更新完成！")
        
    except Exception as e:
        print(f"更新表结构失败: {e}")
        db.session.rollback()

def main():
    """主函数"""
    app = create_app()
    with app.app_context():
        print("开始重新设计佣金系统...")
        
        try:
            # 1. 更新表结构
            update_commission_table_structure()
            
            # 2. 重新设计佣金规则
            redesign_commission_tables()
            
            # 3. 创建示例数据
            create_sample_commission_data()
            
            print("\n=== 佣金系统重新设计完成 ===")
            print("新的佣金规则：")
            print("- 所有下级给上级分35%佣金")
            print("- 包括直接支付金额和下级上贡金额")
            print("- 每个用户只有一个上级和多个下级")
            
        except Exception as e:
            print(f"重新设计失败: {e}")
            db.session.rollback()

if __name__ == '__main__':
    main() 