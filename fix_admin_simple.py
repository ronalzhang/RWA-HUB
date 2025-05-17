#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简化版修复管理员表脚本，直接使用psycopg2连接数据库
用法: python fix_admin_simple.py
"""

import os
import sys
import psycopg2
import json
from datetime import datetime
import configparser

# 数据库连接信息
DB_CONFIG = {
    'host': 'localhost',
    'database': 'rwa_hub',
    'user': 'rwa_hub_user',
    'password': 'password'
}

def read_db_config_from_env():
    """从.env文件读取数据库配置"""
    try:
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if not os.path.exists(env_file):
            env_file = os.path.join(os.path.dirname(__file__), 'app', '.env')
        
        if os.path.exists(env_file):
            print(f"从配置文件读取数据库连接: {env_file}")
            config = configparser.ConfigParser()
            config.read(env_file)
            
            # 解析DATABASE_URL
            db_url = os.environ.get('DATABASE_URL', '')
            if not db_url:
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_URL='):
                            db_url = line.split('=', 1)[1].strip()
                            break
            
            if db_url and 'postgresql://' in db_url:
                parts = db_url.replace('postgresql://', '').split('@')
                if len(parts) == 2:
                    user_pass, host_db = parts
                    up_parts = user_pass.split(':')
                    hd_parts = host_db.split('/')
                    
                    if len(up_parts) == 2 and len(hd_parts) >= 2:
                        DB_CONFIG['user'] = up_parts[0]
                        DB_CONFIG['password'] = up_parts[1]
                        DB_CONFIG['host'] = hd_parts[0].split(':')[0]
                        DB_CONFIG['database'] = hd_parts[1].split('?')[0]
                        print(f"成功解析数据库URL: {db_url.replace(up_parts[1], '****')}")
                        return True
            
            print("无法从配置文件解析数据库连接信息")
            return False
        else:
            print(f"配置文件不存在: {env_file}")
            return False
    except Exception as e:
        print(f"读取配置文件出错: {str(e)}")
        return False

def get_connection():
    """获取数据库连接"""
    try:
        print(f"连接到数据库: {DB_CONFIG['host']}/{DB_CONFIG['database']} (用户: {DB_CONFIG['user']})")
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return conn
    except Exception as e:
        print(f"连接数据库失败: {str(e)}")
        return None

def check_admin_table(conn):
    """检查管理员表是否存在"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'admin_users'
                );
            """)
            exists = cursor.fetchone()[0]
            return exists
    except Exception as e:
        print(f"检查表失败: {str(e)}")
        return False

def create_admin_tables(conn):
    """创建管理员相关表"""
    try:
        with conn.cursor() as cursor:
            # 创建管理员表
            cursor.execute("""
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
            """)
            
            # 创建系统配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    updated_by VARCHAR(80)
                );
            """)
            
            # 创建佣金设置表
            cursor.execute("""
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
            """)
            
            # 创建分配等级表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS distribution_levels (
                    id SERIAL PRIMARY KEY,
                    level INTEGER NOT NULL,
                    rate FLOAT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            conn.commit()
            print("管理员相关表创建成功")
            return True
    except Exception as e:
        conn.rollback()
        print(f"创建表失败: {str(e)}")
        return False

def add_admin_user(conn, wallet_address, username, role='super_admin'):
    """添加管理员用户"""
    try:
        with conn.cursor() as cursor:
            # 检查用户是否已存在
            cursor.execute("""
                SELECT COUNT(*) FROM admin_users WHERE wallet_address = %s
            """, (wallet_address,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"管理员已存在: {wallet_address}")
                return True
            
            # 添加管理员
            permissions = json.dumps(["all"]) if role == 'super_admin' else json.dumps([])
            cursor.execute("""
                INSERT INTO admin_users 
                (wallet_address, username, role, permissions, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
            """, (wallet_address, username, role, permissions))
            
            conn.commit()
            print(f"管理员用户添加成功: {username} ({wallet_address}), 角色: {role}")
            return True
    except Exception as e:
        conn.rollback()
        print(f"添加管理员失败: {str(e)}")
        return False

def list_admin_users(conn):
    """列出所有管理员用户"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, wallet_address, username, role, permissions, 
                       created_at, updated_at, last_login 
                FROM admin_users
            """)
            rows = cursor.fetchall()
            
            if not rows:
                print("管理员表中没有数据")
                return False
            
            print(f"找到 {len(rows)} 个管理员用户:")
            for row in rows:
                print(f"ID: {row[0]}, 钱包地址: {row[1]}, 用户名: {row[2]}, 角色: {row[3]}")
                print(f"  权限: {row[4]}")
                print(f"  创建时间: {row[5]}, 更新时间: {row[6]}, 最后登录: {row[7]}")
            
            return True
    except Exception as e:
        print(f"查询管理员用户失败: {str(e)}")
        return False

def list_tables(conn):
    """列出所有表"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"数据库中的表 ({len(tables)}):")
            for table in tables:
                print(f"  - {table}")
            
            return tables
    except Exception as e:
        print(f"查询表列表失败: {str(e)}")
        return []

def main():
    """主函数"""
    # 读取数据库配置
    read_db_config_from_env()
    
    # 连接数据库
    conn = get_connection()
    if not conn:
        print("无法连接数据库，退出")
        return
    
    try:
        # 列出所有表
        tables = list_tables(conn)
        
        # 检查管理员表
        admin_table_exists = check_admin_table(conn)
        if not admin_table_exists:
            print("管理员表不存在，将创建所需表")
            create_admin_tables(conn)
        else:
            print("管理员表已存在")
        
        # 列出管理员用户
        admin_users_exist = list_admin_users(conn)
        
        # 如果没有管理员用户，添加一个测试管理员
        if not admin_users_exist:
            print("没有管理员用户，将添加测试管理员")
            add_admin_user(
                conn, 
                'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd', 
                '测试管理员', 
                'super_admin'
            )
        
        print("\n操作完成")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 