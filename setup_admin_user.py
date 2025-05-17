#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全面的管理员用户设置脚本
用法: python setup_admin_user.py [options]

选项:
    --wallet-address WALLET  管理员钱包地址
    --username USERNAME      管理员用户名
    --role ROLE              管理员角色 (admin 或 super_admin)
    --check                  仅检查表结构和现有管理员
    --force                  强制创建表结构（如果不存在）
    
例如:
    python setup_admin_user.py --wallet-address HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd --username 测试管理员 --role super_admin
    python setup_admin_user.py --check
"""

import sys
import os
import json
import argparse
import traceback
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 尝试导入Flask应用
try:
    # 首先尝试导入app.py中创建的应用实例
    from app import app
except (ImportError, AttributeError):
    try:
        # 如果失败，尝试导入create_app函数
        from app import create_app
        app = create_app()
    except ImportError:
        print("无法导入Flask应用，请确保项目结构正确")
        sys.exit(1)

# 导入数据库和模型
from app.extensions import db
from sqlalchemy import inspect, text, exc

# 尝试导入模型，如果失败则使用SQL操作
try:
    from app.models.admin import AdminUser
    models_available = True
except ImportError:
    models_available = False
    print("警告: 无法导入AdminUser模型，将使用原始SQL操作")

def check_admin_table():
    """检查管理员表是否存在"""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        return 'admin_users' in tables
    except Exception as e:
        print(f"检查表结构失败: {str(e)}")
        return False

def create_admin_table():
    """创建管理员表结构"""
    try:
        # 读取SQL脚本
        sql_file = os.path.join(os.path.dirname(__file__), 'create_admin_tables.sql')
        if not os.path.exists(sql_file):
            print(f"SQL脚本文件不存在: {sql_file}")
            return False
            
        with open(sql_file, 'r') as f:
            sql_script = f.read()
            
        # 执行SQL
        for statement in sql_script.split(';'):
            if statement.strip():
                try:
                    db.session.execute(text(statement))
                    print(f"执行SQL: {statement[:60]}...")
                except Exception as e:
                    print(f"执行SQL失败: {statement[:60]}..., 错误: {str(e)}")
        
        db.session.commit()
        print("管理员表结构创建成功")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"创建表结构失败: {str(e)}")
        print(traceback.format_exc())
        return False

def add_admin_user(wallet_address, username, role='admin'):
    """添加管理员用户"""
    try:
        if models_available:
            # 使用模型方式
            exists = AdminUser.query.filter_by(wallet_address=wallet_address).first()
            if exists:
                print(f"管理员已存在: {wallet_address}")
                return True
                
            admin = AdminUser(
                wallet_address=wallet_address,
                username=username,
                role=role,
                permissions=json.dumps(["all"]) if role == 'super_admin' else json.dumps([]),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(admin)
            db.session.commit()
            print(f"管理员用户添加成功: {username} ({wallet_address}), 角色: {role}")
            return True
        else:
            # 使用原始SQL方式
            sql = """
            INSERT INTO admin_users 
            (wallet_address, username, role, permissions, created_at, updated_at)
            VALUES (:wallet_address, :username, :role, :permissions, NOW(), NOW())
            ON CONFLICT (wallet_address) DO NOTHING
            """
            permissions = json.dumps(["all"]) if role == 'super_admin' else json.dumps([])
            result = db.session.execute(text(sql), {
                'wallet_address': wallet_address,
                'username': username,
                'role': role,
                'permissions': permissions
            })
            db.session.commit()
            if result.rowcount > 0:
                print(f"管理员用户添加成功: {username} ({wallet_address}), 角色: {role}")
            else:
                print(f"管理员已存在: {wallet_address}")
            return True
    except Exception as e:
        db.session.rollback()
        print(f"添加管理员失败: {str(e)}")
        print(traceback.format_exc())
        return False

def list_admin_users():
    """列出所有管理员用户"""
    try:
        if models_available:
            admins = AdminUser.query.all()
            if not admins:
                print("管理员表中没有数据")
                return []
            else:
                print(f"找到 {len(admins)} 个管理员用户:")
                for admin in admins:
                    print(f"ID: {admin.id}, 钱包地址: {admin.wallet_address}, 用户名: {admin.username}, 角色: {admin.role}")
                return admins
        else:
            # 使用原始SQL方式
            sql = "SELECT id, wallet_address, username, role FROM admin_users"
            result = db.session.execute(text(sql))
            rows = result.fetchall()
            if not rows:
                print("管理员表中没有数据")
                return []
            else:
                print(f"找到 {len(rows)} 个管理员用户:")
                for row in rows:
                    print(f"ID: {row[0]}, 钱包地址: {row[1]}, 用户名: {row[2]}, 角色: {row[3]}")
                return rows
    except Exception as e:
        print(f"查询管理员用户失败: {str(e)}")
        print(traceback.format_exc())
        return []

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='管理员用户设置工具')
    parser.add_argument('--wallet-address', help='管理员钱包地址')
    parser.add_argument('--username', help='管理员用户名')
    parser.add_argument('--role', default='admin', choices=['admin', 'super_admin'], help='管理员角色')
    parser.add_argument('--check', action='store_true', help='检查表结构和现有管理员')
    parser.add_argument('--force', action='store_true', help='强制创建表结构')
    args = parser.parse_args()
    
    # 检查环境变量文件
    env_file = os.path.join(os.path.dirname(__file__), 'app', '.env')
    if os.path.exists(env_file):
        print(f"已加载环境变量文件: {env_file}")
    
    # 使用Flask应用上下文
    with app.app_context():
        # 检查数据库连接
        try:
            db_uri = str(db.engine.url)
            print(f"数据库连接: {db_uri.replace('://', '://<用户名>:<密码>@')}")
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            print("请确保环境变量中包含正确的数据库配置")
            return
        
        # 检查表结构
        table_exists = check_admin_table()
        
        # 如果表不存在且用户要求强制创建，或正在检查
        if not table_exists and (args.force or args.check):
            print("管理员表不存在")
            if args.force:
                print("尝试创建表结构...")
                if not create_admin_table():
                    print("无法创建管理员表，请检查数据库权限和配置")
                    return
            elif args.check:
                print("使用 --force 参数可以创建表结构")
                return
        elif not table_exists:
            print("管理员表不存在，使用 --force 参数可以创建表结构")
            return
        
        # 如果仅检查现有管理员
        if args.check:
            list_admin_users()
            return
        
        # 添加管理员
        if args.wallet_address and args.username:
            add_admin_user(args.wallet_address, args.username, args.role)
        else:
            # 如果没有提供足够的参数，列出现有管理员
            list_admin_users()
            print("\n使用示例:")
            print("    python setup_admin_user.py --wallet-address HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd --username 测试管理员 --role super_admin")

if __name__ == "__main__":
    main() 