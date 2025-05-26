#!/usr/bin/env python3
"""
管理员设置脚本
用于创建初始管理员用户和配置系统
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.admin import AdminUser, SystemConfig

def create_initial_admin():
    """创建初始管理员用户"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查是否已有管理员
            existing_admin = AdminUser.query.first()
            if existing_admin:
                print(f"✅ 已存在管理员用户: {existing_admin.wallet_address}")
                return
            
            # 创建初始超级管理员
            # 使用您的正确钱包地址
            admin_address = "HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd"
            
            initial_admin = AdminUser(
                wallet_address=admin_address,
                username="系统管理员",
                role="super_admin"
            )
            
            db.session.add(initial_admin)
            db.session.commit()
            
            print(f"✅ 成功创建初始管理员: {admin_address}")
            
        except Exception as e:
            print(f"❌ 创建管理员失败: {e}")
            db.session.rollback()

def setup_default_configs():
    """设置默认系统配置"""
    app = create_app()
    
    with app.app_context():
        try:
            # 默认配置
            default_configs = {
                'PLATFORM_FEE_BASIS_POINTS': '250',  # 2.5%
                'PLATFORM_FEE_ADDRESS': 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd',
                'ASSET_CREATION_FEE_AMOUNT': '100',  # 100 USDC
                'ASSET_CREATION_FEE_ADDRESS': 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd'
            }
            
            for key, value in default_configs.items():
                existing_config = SystemConfig.query.filter_by(config_key=key).first()
                if not existing_config:
                    config = SystemConfig(
                        config_key=key,
                        config_value=value,
                        description=f'默认配置: {key}'
                    )
                    db.session.add(config)
                    print(f"✅ 设置默认配置: {key} = {value}")
                else:
                    print(f"ℹ️  配置已存在: {key} = {existing_config.config_value}")
            
            db.session.commit()
            print("✅ 默认配置设置完成")
            
        except Exception as e:
            print(f"❌ 设置默认配置失败: {e}")
            db.session.rollback()

def main():
    """主函数"""
    print("🚀 开始设置管理员和系统配置...")
    
    # 创建初始管理员
    create_initial_admin()
    
    # 设置默认配置
    setup_default_configs()
    
    print("✅ 管理员设置完成！")
    print("\n📋 下一步操作：")
    print("1. 访问管理后台: https://rwa-hub.com/admin/v2/settings")
    print("2. 设置收款钱包私钥（加密存储）")
    print("3. 配置支付参数")
    print("4. 添加其他管理员用户")

if __name__ == '__main__':
    main() 