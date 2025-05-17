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

# 导入应用
from app import create_app
from app.extensions import db
from app.models.admin import AdminUser

def add_admin(wallet_address, username, role='admin'):
    """添加新的管理员用户"""
    # 正确获取Flask应用实例
    app = create_app()
    
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
            permissions=json.dumps(['all']),  # 默认所有权限
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            db.session.add(admin)
            db.session.commit()
            print(f"成功添加管理员: {wallet_address}, 角色: {role}")
        except Exception as e:
            db.session.rollback()
            print(f"添加管理员失败: {str(e)}")
            # 如果是缺少字段的错误，提供详细信息
            if "missing column" in str(e).lower() or "has no column" in str(e).lower():
                print("\n可能是表结构与模型不匹配。请检查表结构和模型定义是否一致")
                print("您可以先运行 check_admin_table.py 来检查表结构")
        
def main():
    if len(sys.argv) < 3:
        print("用法: python add_admin_user.py <wallet_address> <username> [role]")
        sys.exit(1)
        
    wallet_address = sys.argv[1]
    username = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else 'admin'
    
    add_admin(wallet_address, username, role)

if __name__ == "__main__":
    main() 