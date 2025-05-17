#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
添加管理员用户的脚本
用法: python add_admin_user.py <wallet_address> <username> [role]
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 尝试导入Flask应用
try:
    # 直接尝试导入app.py中定义的变量app（Flask应用实例）
    from app.py import app
except (ImportError, AttributeError):
    try:
        # 再尝试从app包中导入app
        try:
            from app import app
        except (ImportError, AttributeError):
            # 如果上述都失败，尝试导入create_app函数并创建应用
            from app import create_app
            app = create_app()
    except ImportError:
        print("无法导入Flask应用，请确保项目结构正确")
        sys.exit(1)

# 导入数据库和模型
from app.extensions import db
from app.models.admin import AdminUser

def add_admin(wallet_address, username, role='admin'):
    """添加新的管理员用户"""
    with app.app_context():
        # 检查用户是否已存在
        exists = AdminUser.query.filter_by(wallet_address=wallet_address).first()
        if exists:
            print(f"管理员已存在: {wallet_address}")
            return
        
        # 创建新管理员
        admin = AdminUser(
            wallet_address=wallet_address,
            username=username,
            role=role,
            permissions=json.dumps(["all"]) if role == 'super_admin' else json.dumps([]),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        try:
            db.session.add(admin)
            db.session.commit()
            print(f"管理员添加成功: {username} ({wallet_address})")
        except Exception as e:
            db.session.rollback()
            print(f"添加管理员失败: {str(e)}")

def main():
    """主函数"""
    if len(sys.argv) < 3:
        print(f"用法: {sys.argv[0]} <wallet_address> <username> [role]")
        sys.exit(1)
    
    wallet_address = sys.argv[1]
    username = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else 'admin'
    
    if role not in ['admin', 'super_admin']:
        print(f"角色必须是 'admin' 或 'super_admin'，不是 '{role}'")
        sys.exit(1)
    
    print(f"添加管理员: {wallet_address}, 用户名: {username}, 角色: {role}")
    add_admin(wallet_address, username, role)

if __name__ == "__main__":
    main() 