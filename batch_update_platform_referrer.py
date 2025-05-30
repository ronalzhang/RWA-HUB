#!/usr/bin/env python3
"""
批量更新现有用户的推荐关系
将所有无推荐人的用户设置为平台的下线
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.commission_config import CommissionConfig

def batch_update_platform_referrer():
    """批量更新现有用户的推荐关系"""
    app = create_app()
    
    with app.app_context():
        try:
            # 获取平台推荐人配置
            enable_platform_referrer = CommissionConfig.get_config('enable_platform_referrer', True)
            platform_referrer_address = CommissionConfig.get_config('platform_referrer_address', '')
            
            if not enable_platform_referrer:
                print("❌ 平台推荐人功能未启用")
                return
                
            if not platform_referrer_address:
                print("❌ 未配置平台推荐人地址")
                return
            
            print(f"🔧 开始批量更新推荐关系...")
            print(f"📍 平台推荐人地址: {platform_referrer_address}")
            
            # 查找所有没有推荐人的用户（排除平台地址本身）
            users_without_referrer = User.query.filter(
                User.referrer_address.is_(None),
                User.eth_address != platform_referrer_address,
                User.solana_address != platform_referrer_address
            ).all()
            
            if not users_without_referrer:
                print("✅ 没有需要更新的用户")
                return
            
            print(f"📊 找到 {len(users_without_referrer)} 个无推荐人用户")
            
            # 批量更新
            updated_count = 0
            for user in users_without_referrer:
                user.referrer_address = platform_referrer_address
                updated_count += 1
                
                # 显示进度
                if updated_count % 10 == 0:
                    print(f"⏳ 已更新 {updated_count}/{len(users_without_referrer)} 用户...")
            
            # 提交更改
            db.session.commit()
            
            print(f"✅ 批量更新完成！")
            print(f"📈 总计更新: {updated_count} 个用户")
            print(f"💰 平台将从这些用户获得35%佣金收益")
            
            # 显示一些样例用户
            print(f"\n📋 更新的用户样例:")
            for i, user in enumerate(users_without_referrer[:5]):
                wallet_addr = user.eth_address or user.solana_address or "未知"
                print(f"  {i+1}. {user.username} ({wallet_addr[:12]}...)")
            
            if len(users_without_referrer) > 5:
                print(f"  ... 还有 {len(users_without_referrer) - 5} 个用户")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 批量更新失败: {str(e)}")
            return False
            
        return True

def show_platform_stats():
    """显示平台推荐人统计信息"""
    app = create_app()
    
    with app.app_context():
        try:
            platform_referrer_address = CommissionConfig.get_config('platform_referrer_address', '')
            
            if not platform_referrer_address:
                print("❌ 未配置平台推荐人地址")
                return
            
            # 统计平台下线数量
            platform_users = User.query.filter_by(referrer_address=platform_referrer_address).all()
            
            print(f"\n📊 平台推荐人统计:")
            print(f"🏆 平台地址: {platform_referrer_address}")
            print(f"👥 平台下线总数: {len(platform_users)}")
            
            # 按钱包类型分类
            eth_users = [u for u in platform_users if u.eth_address]
            solana_users = [u for u in platform_users if u.solana_address]
            
            print(f"🔸 以太坊用户: {len(eth_users)}")
            print(f"🔸 Solana用户: {len(solana_users)}")
            
            # 活跃用户
            from datetime import datetime, timedelta
            recent_users = [u for u in platform_users if u.last_login_at and 
                          u.last_login_at > datetime.utcnow() - timedelta(days=30)]
            print(f"🔸 30天内活跃: {len(recent_users)}")
            
        except Exception as e:
            print(f"❌ 获取统计信息失败: {str(e)}")

if __name__ == "__main__":
    print("🚀 RWA-HUB 平台推荐人批量更新工具")
    print("=" * 50)
    
    # 先显示当前统计
    show_platform_stats()
    
    # 确认是否执行更新
    print(f"\n⚠️  即将将所有无推荐人用户设置为平台的下线")
    confirm = input("确认执行批量更新？(y/N): ")
    
    if confirm.lower() in ['y', 'yes']:
        success = batch_update_platform_referrer()
        if success:
            print(f"\n" + "=" * 50)
            show_platform_stats()  # 再次显示更新后的统计
    else:
        print("❌ 已取消更新") 