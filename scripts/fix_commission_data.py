#!/usr/bin/env python3
"""
修复佣金数据插入问题
使用正确的数据类型插入示例佣金数据
"""
from app import create_app
from app.models import db
from datetime import datetime

def create_sample_commission_data():
    """创建示例佣金数据，使用正确的数据类型"""
    print("=== 创建示例佣金数据 ===")
    
    try:
        # 清理旧的佣金记录
        db.session.execute(db.text("DELETE FROM commission_records"))
        
        # 创建示例佣金记录（使用integer类型的transaction_id）
        sample_records = [
            # 场景1：test_user_1 直接支付100 USDC，admin_user获得35 USDC佣金
            {
                'transaction_id': 1001,  # 使用integer
                'asset_id': 1,
                'payer_address': '0x1234567890123456789012345678901234567890',
                'recipient_address': 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4',
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
                'transaction_id': 1002,  # 使用integer
                'asset_id': 2,
                'payer_address': '0x2345678901234567890123456789012345678901',
                'recipient_address': 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4',
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
                'transaction_id': 1003,  # 使用integer
                'asset_id': 3,
                'payer_address': '0x1234567890123456789012345678901234567890',
                'recipient_address': 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4',
                'amount': 17.5,
                'currency': 'USDC',
                'commission_type': 'upstream_commission',
                'source_amount': 50.0,
                'commission_rate': 35.0,
                'status': 'pending',
                'description': 'test_user_1的下级上贡50 USDC，再分35%给admin_user'
            },
            # 场景4：平台佣金示例
            {
                'transaction_id': 1004,  # 使用integer
                'asset_id': 1,
                'payer_address': 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4',
                'recipient_address': 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4',
                'amount': 15.0,
                'currency': 'USDC',
                'commission_type': 'platform_commission',
                'source_amount': 100.0,
                'commission_rate': 15.0,
                'status': 'paid',
                'description': '平台收取15%手续费'
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
        
        # 显示统计信息
        result = db.session.execute(db.text("""
            SELECT 
                commission_type,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                AVG(commission_rate) as avg_rate
            FROM commission_records 
            GROUP BY commission_type
        """))
        
        print("\n=== 佣金统计 ===")
        for row in result.fetchall():
            print(f"{row[0]}: {row[1]}条记录, 总金额: {row[2]} USDC, 平均费率: {row[3]}%")
        
    except Exception as e:
        print(f"创建示例数据失败: {e}")
        db.session.rollback()

def main():
    """主函数"""
    app = create_app()
    with app.app_context():
        print("开始修复佣金数据...")
        
        try:
            create_sample_commission_data()
            
            print("\n=== 修复完成 ===")
            print("新的35%分佣规则已生效：")
            print("- 所有下级给上级分35%佣金")
            print("- 包括直接支付金额和下级上贡金额")
            print("- 每个用户只有一个上级和多个下级")
            
        except Exception as e:
            print(f"修复失败: {e}")
            db.session.rollback()

if __name__ == '__main__':
    main() 