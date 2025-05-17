#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务器端检查管理员表结构和数据的脚本
用法: python server_check_admin.py [--fix]
"""

import sys
import os
import argparse
import json
import traceback
from datetime import datetime
import importlib.util

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 直接导入app.py文件
try:
    # 使用importlib动态导入app.py文件
    spec = importlib.util.spec_from_file_location("app_module", os.path.join(os.path.dirname(__file__), "app.py"))
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    app = app_module.app
except Exception as e:
    print(f"无法导入app.py: {str(e)}")
    sys.exit(1)

# 导入数据库
from app.extensions import db
from sqlalchemy import inspect, text

def inspect_table(inspector, table_name):
    """检查表结构"""
    print(f"\n===== 表结构: {table_name} =====")
    try:
        columns = inspector.get_columns(table_name)
        for column in columns:
            print(f"列名: {column['name']}, 类型: {column['type']}, 可空: {column.get('nullable', True)}")
        
        pk = inspector.get_pk_constraint(table_name)
        print(f"主键: {pk['constrained_columns']}")
        
        print(f"表存在: 是")
        return True
    except Exception as e:
        print(f"表存在: 否 (错误: {str(e)})")
        return False

def check_admin_users():
    """检查管理员用户表数据"""
    print("\n===== 管理员用户数据 =====")
    try:
        # 使用原始SQL查询
        result = db.session.execute(text("SELECT id, wallet_address, username, role FROM admin_users"))
        rows = result.fetchall()
        if not rows:
            print("管理员表中没有数据")
            return False
        else:
            print(f"找到 {len(rows)} 个管理员用户:")
            for row in rows:
                print(f"ID: {row[0]}, 钱包地址: {row[1]}, 用户名: {row[2]}, 角色: {row[3]}")
            return True
    except Exception as e:
        print(f"查询管理员用户数据失败: {str(e)}")
        print(traceback.format_exc())
        return False

def execute_raw_sql(sql):
    """执行原始SQL查询"""
    try:
        result = db.session.execute(text(sql))
        return result.fetchall()
    except Exception as e:
        print(f"执行SQL失败: {str(e)}")
        return []

def fix_admin_table():
    """修复管理员表"""
    try:
        # 执行SQL脚本创建表
        print("\n尝试创建管理员表...")
        
        # 创建管理员表的SQL
        sql_statements = [
            """
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
            """,
            """
            CREATE TABLE IF NOT EXISTS system_config (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT NOW(),
                updated_by VARCHAR(80)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS commission_settings (
                id SERIAL PRIMARY KEY,
                asset_type_id INTEGER,
                commission_rate FLOAT NOT NULL,
                min_amount FLOAT,
                max_amount FLOAT,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS distribution_levels (
                id SERIAL PRIMARY KEY,
                level INTEGER NOT NULL,
                rate FLOAT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
        ]
            
        # 执行SQL
        for statement in sql_statements:
            try:
                db.session.execute(text(statement))
                print(f"执行SQL: {statement[:60]}...")
            except Exception as e:
                print(f"执行SQL失败: {statement[:60]}..., 错误: {str(e)}")
        
        db.session.commit()
        print("SQL脚本执行完成")
        
        # 添加测试管理员
        try:
            admin_sql = """
            INSERT INTO admin_users (wallet_address, username, role, permissions, created_at, updated_at)
            VALUES ('HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd', '测试管理员', 'super_admin', '["all"]', NOW(), NOW())
            ON CONFLICT (wallet_address) DO NOTHING
            """
            db.session.execute(text(admin_sql))
            db.session.commit()
            print("测试管理员添加成功")
        except Exception as e:
            db.session.rollback()
            print(f"添加测试管理员失败: {str(e)}")
        
        return True
    except Exception as e:
        db.session.rollback()
        print(f"修复管理员表失败: {str(e)}")
        print(traceback.format_exc())
        return False

def add_admin_user(wallet_address, username, role='admin'):
    """添加管理员用户"""
    try:
        # 检查用户是否已存在
        result = db.session.execute(
            text("SELECT COUNT(*) FROM admin_users WHERE wallet_address = :addr"),
            {"addr": wallet_address}
        )
        count = result.scalar()
        if count > 0:
            print(f"管理员已存在: {wallet_address}")
            return True
        
        # 添加管理员
        permissions = json.dumps(["all"]) if role == 'super_admin' else json.dumps([])
        sql = """
        INSERT INTO admin_users 
        (wallet_address, username, role, permissions, created_at, updated_at)
        VALUES (:wallet_address, :username, :role, :permissions, NOW(), NOW())
        """
        db.session.execute(text(sql), {
            'wallet_address': wallet_address,
            'username': username,
            'role': role,
            'permissions': permissions
        })
        db.session.commit()
        print(f"管理员用户添加成功: {username} ({wallet_address}), 角色: {role}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"添加管理员失败: {str(e)}")
        print(traceback.format_exc())
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='检查管理员表结构和数据')
    parser.add_argument('--fix', action='store_true', help='修复表结构问题')
    parser.add_argument('--add', action='store_true', help='添加测试管理员')
    parser.add_argument('--wallet', help='管理员钱包地址')
    parser.add_argument('--username', help='管理员用户名')
    parser.add_argument('--role', default='super_admin', choices=['admin', 'super_admin'], help='管理员角色')
    args = parser.parse_args()
    
    print("开始检查数据库表结构...")
    
    # 使用Flask应用上下文
    with app.app_context():
        # 输出数据库连接信息（排除敏感信息）
        try:
            print(f"数据库类型: {db.engine.name}")
            print(f"数据库服务器: {db.engine.url.host}")
            print(f"数据库名称: {db.engine.url.database}")
        except Exception as e:
            print(f"无法获取数据库信息: {str(e)}")
        
        # 获取数据库检查器
        inspector = inspect(db.engine)
        
        # 列出所有表
        tables = inspector.get_table_names()
        print(f"数据库中的表 ({len(tables)}): {', '.join(tables)}")
        
        # 检查管理员相关表结构
        admin_tables = ['admin_users', 'system_config', 'commission_settings', 'distribution_levels']
        
        missing_tables = []
        for table in admin_tables:
            if table in tables:
                exists = inspect_table(inspector, table)
                if not exists:
                    missing_tables.append(table)
            else:
                print(f"\n表 {table} 不存在")
                missing_tables.append(table)
        
        # 检查管理员用户数据
        admin_data_exists = False
        if 'admin_users' in tables:
            admin_data_exists = check_admin_users()
        
        # 如果admin_users表存在但没有数据，可以查看其他关键表
        if 'admin_users' in tables and not admin_data_exists:
            # 尝试使用原始SQL查询
            print("\n使用原始SQL查询admin_users表:")
            rows = execute_raw_sql("SELECT * FROM admin_users LIMIT 5")
            if rows:
                print("原始查询结果:")
                for row in rows:
                    print(row)
            else:
                print("原始查询未返回任何数据")
        
        # 如果有表缺失并且用户要求修复，尝试修复
        if missing_tables and args.fix:
            print(f"\n需要修复的表: {', '.join(missing_tables)}")
            success = fix_admin_table()
            if success:
                print("\n表结构已修复，请重新运行此脚本检查修复结果")
            else:
                print("\n表结构修复失败")
        elif missing_tables:
            print(f"\n存在表结构问题，请使用 --fix 参数运行此脚本以尝试修复")
        else:
            print("\n所有管理员相关表结构正常")
        
        # 添加管理员
        if args.add or (args.wallet and args.username):
            wallet = args.wallet or 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd'
            username = args.username or '测试管理员'
            add_admin_user(wallet, username, args.role)
        
        print("\n检查完成!")

if __name__ == "__main__":
    main() 