#!/usr/bin/env python3
"""
完整的佣金系统初始化脚本
包括：数据库表创建、配置初始化、示例数据创建
"""
from app import create_app
from app.models import db
from app.models.commission_config import CommissionConfig, UserCommissionBalance
from datetime import datetime

def init_commission_system():
    """初始化佣金系统"""
    print("=== 初始化佣金系统 ===")
    
    try:
        # 1. 创建数据库表
        print("1. 创建数据库表...")
        
        # 创建commission_config表
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS commission_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                description VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 创建user_commission_balance表
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS user_commission_balance (
                id SERIAL PRIMARY KEY,
                user_address VARCHAR(64) UNIQUE NOT NULL,
                total_earned DECIMAL(20,8) DEFAULT 0,
                available_balance DECIMAL(20,8) DEFAULT 0,
                withdrawn_amount DECIMAL(20,8) DEFAULT 0,
                frozen_amount DECIMAL(20,8) DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'USDC',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        db.session.commit()
        print("✅ 数据库表创建完成")
        
        # 2. 初始化佣金配置
        print("2. 初始化佣金配置...")
        
        configs = [
            # 35%分佣规则配置
            ('commission_rate', 35.0, '推荐佣金比例设置'),
            ('commission_description', '推荐好友享受35%佣金奖励', '佣金功能描述文案'),
            
            # 分享按钮配置
            ('share_button_text', '分享赚佣金', '分享按钮显示文案'),
            ('share_description', '分享此项目给好友，好友购买后您将获得35%佣金奖励', '分享功能说明文案'),
            ('share_success_message', '分享链接已复制，快去邀请好友吧！', '分享成功后的提示信息'),
            
            # 提现配置
            ('min_withdraw_amount', 10.0, '用户提现的最低金额限制'),
            ('withdraw_fee_rate', 0.0, '提现时收取的手续费比例'),
            ('withdraw_description', '最低提现金额10 USDC，提现将转入您的钱包地址', '提现功能说明文案'),
            
            # 佣金计算规则说明
            ('commission_rules', {
                'direct_commission': '直接推荐佣金：好友购买金额的35%',
                'indirect_commission': '间接推荐佣金：下级佣金收益的35%',
                'settlement_time': '佣金实时到账，可随时提现',
                'currency': 'USDC'
            }, '佣金计算规则详细说明')
        ]
        
        for key, value, description in configs:
            CommissionConfig.set_config(key, value, description)
            print(f"✅ 设置配置: {key}")
        
        # 3. 创建示例佣金余额数据
        print("3. 创建示例佣金余额数据...")
        
        # 为现有用户创建佣金余额记录
        result = db.session.execute(db.text("SELECT eth_address FROM users"))
        user_addresses = [row[0] for row in result.fetchall()]
        
        for address in user_addresses:
            balance = UserCommissionBalance.get_balance(address)
            # 为示例用户添加一些佣金余额
            if address == 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4':  # admin_user
                UserCommissionBalance.update_balance(address, 150.0, 'add')
                print(f"✅ 为管理员用户添加150 USDC佣金余额")
            else:
                UserCommissionBalance.update_balance(address, 50.0, 'add')
                print(f"✅ 为用户 {address[:10]}... 添加50 USDC佣金余额")
        
        # 4. 更新现有用户为分销商
        print("4. 更新现有用户为分销商...")
        db.session.execute(db.text("UPDATE users SET is_distributor = TRUE WHERE is_distributor = FALSE"))
        db.session.commit()
        print("✅ 所有用户已设置为分销商")
        
        print("\n=== 佣金系统初始化完成 ===")
        print("📊 配置统计:")
        print(f"   - 佣金比例: 35%")
        print(f"   - 最低提现: 10 USDC")
        print(f"   - 提现手续费: 0%")
        print(f"   - 用户佣金余额记录: {len(user_addresses)}个")
        print("\n🎯 功能说明:")
        print("   - 所有用户都是分销商，享受35%推荐奖励")
        print("   - 佣金实时到账，可在钱包中查看余额")
        print("   - 支持提现到外部钱包地址")
        print("   - 前端可调用API获取分享配置和佣金余额")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 初始化失败: {str(e)}")
        raise

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        init_commission_system() 