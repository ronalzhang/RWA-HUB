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

# 导入应用
from app import create_app
from app.extensions import db
from sqlalchemy import inspect, text, exc

# 尝试导入模型，如果失败则使用SQL操作
try:
    from app.models.admin import AdminUser
    models_available = True
except Exception as e:
    print(f"警告: 无法导入AdminUser模型: {str(e)}")
    models_available = False

def check_table_exists(inspector, table_name):
    """检查表是否存在"""
    return table_name in inspector.get_table_names()

def check_admin_exists(wallet_address):
    """检查管理员是否已存在"""
    if models_available:
        try:
            admin = AdminUser.query.filter_by(wallet_address=wallet_address).first()
            return admin is not None
        except Exception as e:
            print(f"通过ORM检查管理员失败: {str(e)}")
    
    # 使用原始SQL查询
    try:
        result = db.session.execute(
            text("SELECT COUNT(*) FROM admin_users WHERE wallet_address = :addr"),
            {"addr": wallet_address}
        )
        count = result.scalar()
        return count > 0
    except Exception as e:
        print(f"通过SQL检查管理员失败: {str(e)}")
        return False

def list_existing_admins():
    """列出现有的管理员"""
    print("\n===== 现有管理员 =====")
    if models_available:
        try:
            admins = AdminUser.query.all()
            if not admins:
                print("  没有找到管理员")
            else:
                for admin in admins:
                    print(f"  ID: {admin.id}, 钱包地址: {admin.wallet_address}, 用户名: {admin.username}, 角色: {admin.role}")
        except Exception as e:
            print(f"  通过ORM列出管理员失败: {str(e)}")
            # 回退到使用SQL
            try:
                result = db.session.execute(text("SELECT id, wallet_address, username, role FROM admin_users"))
                rows = result.fetchall()
                if not rows:
                    print("  没有找到管理员")
                else:
                    for row in rows:
                        print(f"  ID: {row[0]}, 钱包地址: {row[1]}, 用户名: {row[2]}, 角色: {row[3]}")
            except Exception as e2:
                print(f"  通过SQL列出管理员也失败: {str(e2)}")
    else:
        # 使用原始SQL查询
        try:
            result = db.session.execute(text("SELECT id, wallet_address, username, role FROM admin_users"))
            rows = result.fetchall()
            if not rows:
                print("  没有找到管理员")
            else:
                for row in rows:
                    print(f"  ID: {row[0]}, 钱包地址: {row[1]}, 用户名: {row[2]}, 角色: {row[3]}")
        except Exception as e:
            print(f"  通过SQL列出管理员失败: {str(e)}")

def create_admin_tables():
    """创建管理员相关表"""
    print("\n尝试创建管理员相关表...")
    try:
        # 从SQL文件中读取创建表的SQL
        sql_file = os.path.join(os.path.dirname(__file__), 'create_admin_tables.sql')
        if not os.path.exists(sql_file):
            sql_file = os.path.join(os.path.dirname(__file__), 'scripts', 'setup', 'create_admin_tables.sql')
            
        if not os.path.exists(sql_file):
            print(f"找不到SQL文件: create_admin_tables.sql")
            # 内联定义创建表的SQL
            sql_script = """
            -- 管理员用户表
            CREATE TABLE IF NOT EXISTS admin_users (
                id SERIAL PRIMARY KEY,
                wallet_address VARCHAR(100) UNIQUE NOT NULL,
                username VARCHAR(50),
                role VARCHAR(20) NOT NULL DEFAULT 'admin',
                permissions TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                last_login TIMESTAMP
            );
            """
        else:
            with open(sql_file, 'r') as f:
                sql_script = f.read()
        
        # 按语句拆分并执行
        for statement in sql_script.split(';'):
            if statement.strip():
                try:
                    db.session.execute(text(statement))
                    print(f"  执行SQL: {statement[:60]}...")
                except Exception as e:
                    print(f"  执行SQL失败: {statement[:60]}..., 错误: {str(e)}")
        
        db.session.commit()
        print("  SQL脚本执行完成")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"  创建管理员表失败: {str(e)}")
        return False

def add_admin_user(wallet_address, username, role='admin'):
    """添加管理员用户"""
    print(f"\n尝试添加管理员: {wallet_address}...")
    
    # 检查管理员是否已存在
    if check_admin_exists(wallet_address):
        print(f"  管理员已存在: {wallet_address}")
        return True
    
    # 添加管理员
    if models_available:
        try:
            # 使用ORM添加管理员
            admin = AdminUser(
                wallet_address=wallet_address,
                username=username,
                role=role,
                permissions=json.dumps(['all']),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(admin)
            db.session.commit()
            print(f"  成功添加管理员: {wallet_address}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"  通过ORM添加管理员失败: {str(e)}")
            print("  将尝试使用原始SQL添加")
    
    # 使用原始SQL添加管理员
    try:
        sql = """
        INSERT INTO admin_users (wallet_address, username, role, permissions, created_at, updated_at)
        VALUES (:wallet_address, :username, :role, :permissions, :created_at, :updated_at)
        """
        
        db.session.execute(text(sql), {
            'wallet_address': wallet_address,
            'username': username,
            'role': role,
            'permissions': json.dumps(['all']),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        db.session.commit()
        print(f"  成功通过SQL添加管理员: {wallet_address}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"  通过SQL添加管理员失败: {str(e)}")
        return False

def check_tables():
    """检查数据库表结构"""
    print("\n===== 检查数据库表结构 =====")
    try:
        # 获取数据库检查器
        inspector = inspect(db.engine)
        
        # 列出所有表
        tables = inspector.get_table_names()
        print(f"数据库中的表 ({len(tables)}): {', '.join(tables)}")
        
        # 检查管理员相关表
        admin_tables = ['admin_users', 'system_config', 'commission_settings', 'distribution_levels']
        missing_tables = []
        
        for table in admin_tables:
            exists = table in tables
            print(f"表 {table}: {'存在' if exists else '不存在'}")
            if not exists:
                missing_tables.append(table)
        
        return missing_tables
    except Exception as e:
        print(f"检查表结构失败: {str(e)}")
        return admin_tables  # 假设所有表都缺失

def main():
    parser = argparse.ArgumentParser(description='管理员用户设置工具')
    parser.add_argument('--wallet-address', help='管理员钱包地址')
    parser.add_argument('--username', help='管理员用户名')
    parser.add_argument('--role', default='admin', choices=['admin', 'super_admin'], help='管理员角色')
    parser.add_argument('--check', action='store_true', help='仅检查表结构和现有管理员')
    parser.add_argument('--force', action='store_true', help='强制创建表结构（如果不存在）')
    args = parser.parse_args()
    
    # 如果没有任何参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        # 输出数据库连接信息
        engine = db.engine
        print(f"数据库类型: {engine.name}")
        print(f"数据库URL: {engine.url.host}/{engine.url.database}")
        
        # 检查表结构
        missing_tables = check_tables()
        
        # 如果有缺失的表并且指定了--force，或者是check模式，创建表
        if missing_tables and (args.force or args.check):
            print(f"\n缺失的表: {', '.join(missing_tables)}")
            if args.force:
                create_admin_tables()
        
        # 列出现有管理员
        list_existing_admins()
        
        # 如果不是仅检查模式并且提供了钱包地址，添加管理员
        if not args.check and args.wallet_address:
            if not args.username:
                print("\n错误: 添加管理员需要指定用户名参数 --username")
                sys.exit(1)
            
            # 添加管理员
            add_admin_user(args.wallet_address, args.username, args.role)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"执行出错: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1) 