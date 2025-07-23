#!/usr/bin/env python3
"""
初始化佣金管理基础数据脚本
根据需求文档初始化佣金设置、分销等级等基础数据
"""
from app import create_app
from app.models import db
from app.models.admin import CommissionSetting
from datetime import datetime

def init_commission_settings():
    """初始化佣金设置"""
    print("=== 初始化佣金设置 ===")
    
    # 全局佣金设置
    global_settings = [
        {
            'asset_type_id': None,  # 全局设置
            'commission_rate': 3.5,  # 3.5%
            'min_amount': 0.01,
            'max_amount': 10000.0,
            'is_active': True,
            'created_by': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
            'description': '全局默认佣金设置'
        }
    ]
    
    # 特定资产类型佣金设置
    asset_type_settings = [
        {
            'asset_type_id': 10,  # 不动产
            'commission_rate': 0.01,  # 0.01%
            'min_amount': 100.0,
            'max_amount': 2000000.0,
            'is_active': True,
            'created_by': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
            'description': '不动产上链佣金设置'
        },
        {
            'asset_type_id': 20,  # 类不动产
            'commission_rate': 0.01,  # 0.01%
            'min_amount': 100.0,
            'max_amount': 3000000.0,
            'is_active': True,
            'created_by': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
            'description': '类不动产上链佣金设置'
        }
    ]
    
    all_settings = global_settings + asset_type_settings
    
    for setting_data in all_settings:
        # 检查是否已存在
        existing = CommissionSetting.query.filter_by(
            asset_type_id=setting_data['asset_type_id']
        ).first()
        
        if not existing:
            setting = CommissionSetting(
                asset_type_id=setting_data['asset_type_id'],
                commission_rate=setting_data['commission_rate'],
                min_amount=setting_data['min_amount'],
                max_amount=setting_data['max_amount'],
                is_active=setting_data['is_active'],
                created_by=setting_data['created_by'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(setting)
            print(f"添加佣金设置: {setting_data['description']}")
        else:
            print(f"佣金设置已存在: {setting_data['description']}")
    
    db.session.commit()

def init_distribution_levels():
    """初始化分销等级"""
    print("\n=== 初始化分销等级 ===")
    
    # 检查distribution_levels表是否存在
    try:
        result = db.session.execute(db.text("SELECT COUNT(*) FROM distribution_levels"))
        count = result.scalar()
        print(f"distribution_levels表当前有 {count} 条记录")
        
        if count == 0:
            # 插入分销等级数据
            levels_data = [
                {'level': 1, 'commission_rate': 30.0, 'description': '一级分销（直接推荐人）'},
                {'level': 2, 'commission_rate': 20.0, 'description': '二级分销（间接推荐人）'},
                {'level': 3, 'commission_rate': 10.0, 'description': '三级分销（三级推荐人）'}
            ]
            
            for level_data in levels_data:
                db.session.execute(db.text("""
                    INSERT INTO distribution_levels (level, commission_rate, description, is_active, created_at, updated_at)
                    VALUES (:level, :commission_rate, :description, true, NOW(), NOW())
                """), level_data)
                print(f"添加分销等级: {level_data['description']}")
            
            db.session.commit()
        else:
            print("分销等级数据已存在")
            
    except Exception as e:
        print(f"初始化分销等级失败: {e}")

def init_sample_users():
    """初始化示例用户数据（基于钱包地址）"""
    print("\n=== 初始化示例用户数据 ===")
    
    # 检查是否有用户数据
    try:
        result = db.session.execute(db.text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        print(f"users表当前有 {count} 条记录")
        
        if count == 0:
            # 插入示例用户数据
            sample_users = [
                {
                    'username': 'admin_user',
                    'email': 'admin@rwahub.com',
                    'eth_address': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
                    'role': 'admin',
                    'status': 'active'
                },
                {
                    'username': 'test_user_1',
                    'email': 'user1@test.com',
                    'eth_address': '0x1234567890123456789012345678901234567890',
                    'role': 'user',
                    'status': 'active'
                },
                {
                    'username': 'test_user_2',
                    'email': 'user2@test.com',
                    'eth_address': '0x2345678901234567890123456789012345678901',
                    'role': 'user',
                    'status': 'active'
                }
            ]
            
            for user_data in sample_users:
                db.session.execute(db.text("""
                    INSERT INTO users (username, email, eth_address, role, status, is_active, created_at, updated_at)
                    VALUES (:username, :email, :eth_address, :role, :status, true, NOW(), NOW())
                """), user_data)
                print(f"添加示例用户: {user_data['username']} ({user_data['eth_address']})")
            
            db.session.commit()
        else:
            print("用户数据已存在")
            
    except Exception as e:
        print(f"初始化示例用户失败: {e}")

def init_sample_commission_records():
    """初始化示例佣金记录"""
    print("\n=== 初始化示例佣金记录 ===")
    
    try:
        # 检查是否有新的佣金记录（非旧的以太坊地址）
        result = db.session.execute(db.text("""
            SELECT COUNT(*) FROM commission_records 
            WHERE recipient_address != '0x0000000000000000000000000000000000000000'
        """))
        count = result.scalar()
        print(f"有效佣金记录数量: {count}")
        
        if count == 0:
            # 插入示例佣金记录
            sample_records = [
                {
                    'transaction_id': 'sample_tx_001',
                    'asset_id': 1,
                    'recipient_address': '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b',
                    'amount': 100.50,
                    'currency': 'USDC',
                    'commission_type': 'platform',
                    'status': 'paid'
                },
                {
                    'transaction_id': 'sample_tx_002',
                    'asset_id': 2,
                    'recipient_address': '0x1234567890123456789012345678901234567890',
                    'amount': 50.25,
                    'currency': 'USDC',
                    'commission_type': 'referral_1',
                    'referral_level': 1,
                    'status': 'pending'
                },
                {
                    'transaction_id': 'sample_tx_003',
                    'asset_id': 2,
                    'recipient_address': '0x2345678901234567890123456789012345678901',
                    'amount': 25.10,
                    'currency': 'USDC',
                    'commission_type': 'referral_2',
                    'referral_level': 2,
                    'status': 'pending'
                }
            ]
            
            for record_data in sample_records:
                db.session.execute(db.text("""
                    INSERT INTO commission_records 
                    (transaction_id, asset_id, recipient_address, amount, currency, commission_type, referral_level, status, created_at, updated_at)
                    VALUES (:transaction_id, :asset_id, :recipient_address, :amount, :currency, :commission_type, :referral_level, :status, NOW(), NOW())
                """), record_data)
                print(f"添加示例佣金记录: {record_data['transaction_id']} - {record_data['amount']} {record_data['currency']}")
            
            db.session.commit()
        else:
            print("有效佣金记录已存在")
            
    except Exception as e:
        print(f"初始化示例佣金记录失败: {e}")

def main():
    """主函数"""
    app = create_app()
    with app.app_context():
        print("开始初始化佣金管理基础数据...")
        
        try:
            # 初始化各种基础数据
            init_commission_settings()
            init_distribution_levels()
            init_sample_users()
            init_sample_commission_records()
            
            print("\n=== 初始化完成 ===")
            print("佣金管理基础数据初始化成功！")
            
        except Exception as e:
            print(f"初始化失败: {e}")
            db.session.rollback()

if __name__ == '__main__':
    main() 