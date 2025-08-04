#!/usr/bin/env python3
"""
PostgreSQL 数据迁移脚本
从 rwa_hub_data_export.sql 文件迁移数据到 PostgreSQL 数据库
"""

import os
import sys
import re
import psycopg2
from datetime import datetime
import json

# PostgreSQL 连接配置
PG_CONFIG = {
    'host': 'localhost',
    'database': 'rwa_hub',
    'user': 'rwa_hub_user',
    'password': 'password',
    'port': 5432
}

def connect_postgresql():
    """连接 PostgreSQL 数据库"""
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"❌ 连接 PostgreSQL 失败: {e}")
        return None

def read_sql_export():
    """读取SQL导出文件"""
    sql_file = 'rwa_hub_data_export.sql'
    
    if not os.path.exists(sql_file):
        print(f"❌ 错误: 找不到SQL导出文件 {sql_file}")
        return None
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return content

def create_tables_if_not_exist(conn):
    """创建必要的表结构"""
    
    tables_sql = {
        'admin_operation_logs': '''
            CREATE TABLE IF NOT EXISTS admin_operation_logs (
                id SERIAL PRIMARY KEY,
                admin_address TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                operation_details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'admin_users': '''
            CREATE TABLE IF NOT EXISTS admin_users (
                id SERIAL PRIMARY KEY,
                wallet_address TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                permissions TEXT,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'alembic_version': '''
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num TEXT PRIMARY KEY
            )
        ''',
        
        'assets': '''
            CREATE TABLE IF NOT EXISTS assets (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                area REAL,
                location TEXT,
                total_area REAL,
                total_value REAL,
                asset_code TEXT UNIQUE,
                price_per_token REAL,
                total_supply BIGINT,
                contract_address TEXT,
                remaining_supply BIGINT,
                images TEXT,
                documents TEXT,
                status INTEGER DEFAULT 1,
                approved_by TEXT,
                created_by TEXT,
                updated_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                current_supply BIGINT,
                blockchain_info TEXT,
                dividend_rate REAL,
                annual_return REAL,
                is_featured BOOLEAN DEFAULT FALSE,
                risk_level TEXT,
                minimum_investment REAL,
                maximum_investment REAL,
                investment_period TEXT,
                liquidity_score REAL,
                is_active BOOLEAN DEFAULT TRUE,
                metadata TEXT
            )
        ''',
        
        'trades': '''
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                asset_id INTEGER NOT NULL,
                trade_type TEXT NOT NULL,
                quantity BIGINT NOT NULL,
                price_per_token REAL NOT NULL,
                user_address TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_blockchain_confirmed BOOLEAN DEFAULT FALSE,
                blockchain_tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                block_number BIGINT,
                total_amount REAL,
                platform_fee REAL,
                fee_rate REAL,
                referrer_address TEXT,
                commission_paid REAL,
                FOREIGN KEY (asset_id) REFERENCES assets (id)
            )
        ''',
        
        'commission_records': '''
            CREATE TABLE IF NOT EXISTS commission_records (
                id SERIAL PRIMARY KEY,
                trade_id INTEGER NOT NULL,
                asset_id INTEGER NOT NULL,
                recipient_address TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USDC',
                commission_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                transaction_hash TEXT,
                FOREIGN KEY (trade_id) REFERENCES trades (id),
                FOREIGN KEY (asset_id) REFERENCES assets (id)
            )
        ''',
        
        'users': '''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                wallet_address TEXT UNIQUE NOT NULL,
                username TEXT,
                email TEXT,
                referrer_address TEXT,
                referral_code TEXT UNIQUE,
                total_invested REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                kyc_status TEXT DEFAULT 'pending',
                risk_tolerance TEXT,
                investment_experience TEXT
            )
        ''',
        
        'dividend_records': '''
            CREATE TABLE IF NOT EXISTS dividend_records (
                id SERIAL PRIMARY KEY,
                asset_id INTEGER NOT NULL,
                user_address TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USDC',
                dividend_date DATE NOT NULL,
                status TEXT DEFAULT 'pending',
                transaction_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES assets (id)
            )
        ''',
        
        'system_configs': '''
            CREATE TABLE IF NOT EXISTS system_configs (
                id SERIAL PRIMARY KEY,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'distribution_levels': '''
            CREATE TABLE IF NOT EXISTS distribution_levels (
                id SERIAL PRIMARY KEY,
                level INTEGER UNIQUE NOT NULL,
                commission_rate REAL NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'commission_config': '''
            CREATE TABLE IF NOT EXISTS commission_config (
                id SERIAL PRIMARY KEY,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'user_commission_balance': '''
            CREATE TABLE IF NOT EXISTS user_commission_balance (
                id SERIAL PRIMARY KEY,
                user_address TEXT UNIQUE NOT NULL,
                available_balance REAL DEFAULT 0,
                pending_balance REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                currency TEXT DEFAULT 'USDC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'commission_withdrawals': '''
            CREATE TABLE IF NOT EXISTS commission_withdrawals (
                id SERIAL PRIMARY KEY,
                user_address TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USDC',
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                transaction_hash TEXT,
                notes TEXT
            )
        ''',
        
        'platform_incomes': '''
            CREATE TABLE IF NOT EXISTS platform_incomes (
                id SERIAL PRIMARY KEY,
                source_type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USDC',
                trade_id INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transaction_hash TEXT
            )
        ''',
        
        'dashboard_stats': '''
            CREATE TABLE IF NOT EXISTS dashboard_stats (
                id SERIAL PRIMARY KEY,
                stat_key TEXT UNIQUE NOT NULL,
                stat_value TEXT,
                stat_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'distribution_settings': '''
            CREATE TABLE IF NOT EXISTS distribution_settings (
                id SERIAL PRIMARY KEY,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'short_links': '''
            CREATE TABLE IF NOT EXISTS short_links (
                id SERIAL PRIMARY KEY,
                original_url TEXT NOT NULL,
                short_code TEXT UNIQUE NOT NULL,
                user_address TEXT,
                click_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''',
        
        'ip_visits': '''
            CREATE TABLE IF NOT EXISTS ip_visits (
                id SERIAL PRIMARY KEY,
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                referrer TEXT,
                page_url TEXT,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                country TEXT,
                city TEXT
            )
        ''',
        
        'share_messages': '''
            CREATE TABLE IF NOT EXISTS share_messages (
                id SERIAL PRIMARY KEY,
                message_type TEXT NOT NULL,
                title TEXT,
                content TEXT,
                image_url TEXT,
                link_url TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        
        'commission_settings': '''
            CREATE TABLE IF NOT EXISTS commission_settings (
                id SERIAL PRIMARY KEY,
                level INTEGER NOT NULL,
                commission_rate REAL NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
    }
    
    cursor = conn.cursor()
    
    for table_name, create_sql in tables_sql.items():
        try:
            cursor.execute(create_sql)
            print(f"✓ 表 {table_name} 创建成功或已存在")
        except Exception as e:
            print(f"✗ 创建表 {table_name} 失败: {e}")
    
    conn.commit()

def parse_insert_statements(sql_content):
    """解析INSERT语句"""
    # 匹配INSERT语句的正则表达式
    insert_pattern = r"INSERT INTO public\.(\w+) VALUES \((.*?)\);"
    
    statements = {}
    
    for match in re.finditer(insert_pattern, sql_content, re.DOTALL):
        table_name = match.group(1)
        values_str = match.group(2)
        
        if table_name not in statements:
            statements[table_name] = []
        
        # 解析值
        values = parse_values(values_str)
        statements[table_name].append(values)
    
    return statements

def parse_values(values_str):
    """解析INSERT语句中的值"""
    values = []
    current_value = ""
    in_quotes = False
    quote_char = None
    paren_count = 0
    
    i = 0
    while i < len(values_str):
        char = values_str[i]
        
        if not in_quotes:
            if char in ("'", '"'):
                in_quotes = True
                quote_char = char
                current_value += char
            elif char == '(':
                paren_count += 1
                current_value += char
            elif char == ')':
                paren_count -= 1
                current_value += char
            elif char == ',' and paren_count == 0:
                values.append(process_value(current_value.strip()))
                current_value = ""
            else:
                current_value += char
        else:
            if char == quote_char:
                # 检查是否是转义的引号
                if i + 1 < len(values_str) and values_str[i + 1] == quote_char:
                    current_value += char + char
                    i += 1  # 跳过下一个字符
                else:
                    in_quotes = False
                    quote_char = None
                    current_value += char
            else:
                current_value += char
        
        i += 1
    
    # 添加最后一个值
    if current_value.strip():
        values.append(process_value(current_value.strip()))
    
    return values

def process_value(value):
    """处理单个值"""
    value = value.strip()
    
    if value == 'NULL':
        return None
    elif value.startswith("'") and value.endswith("'"):
        # 字符串值，去掉引号并处理转义
        return value[1:-1].replace("''", "'").replace("\\'", "'")
    elif value.startswith('"') and value.endswith('"'):
        # 双引号字符串
        return value[1:-1].replace('""', '"').replace('\\"', '"')
    elif value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    else:
        # 尝试转换为数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value

def get_table_columns(conn, table_name):
    """获取表的列信息"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table_name,))
    
    columns = cursor.fetchall()
    return [col[0] for col in columns]

def insert_data(conn, table_name, data_list):
    """插入数据到指定表"""
    if not data_list:
        return
    
    cursor = conn.cursor()
    
    # 获取表的列信息
    column_names = get_table_columns(conn, table_name)
    
    print(f"正在插入数据到表 {table_name}...")
    print(f"表列: {column_names}")
    
    success_count = 0
    error_count = 0
    
    for values in data_list:
        try:
            # 确保值的数量与列的数量匹配
            if len(values) != len(column_names):
                print(f"警告: 表 {table_name} 的值数量({len(values)})与列数量({len(column_names)})不匹配")
                # 如果值太少，用None填充
                while len(values) < len(column_names):
                    values.append(None)
                # 如果值太多，截断
                values = values[:len(column_names)]
            
            placeholders = ','.join(['%s' for _ in values])
            sql = f"INSERT INTO {table_name} ({','.join(column_names)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            cursor.execute(sql, values)
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"插入数据到表 {table_name} 失败: {e}")
            print(f"值: {values}")
    
    conn.commit()
    print(f"表 {table_name}: 成功插入 {success_count} 条记录, 失败 {error_count} 条")

def main():
    """主函数"""
    print("🚀 开始 PostgreSQL 数据迁移...")
    
    # 读取SQL导出文件
    print("1. 读取SQL导出文件...")
    sql_content = read_sql_export()
    if not sql_content:
        return
    
    # 连接PostgreSQL数据库
    print("2. 连接 PostgreSQL 数据库...")
    conn = connect_postgresql()
    if not conn:
        return
    
    try:
        # 创建表结构
        print("3. 创建表结构...")
        create_tables_if_not_exist(conn)
        
        # 解析INSERT语句
        print("4. 解析INSERT语句...")
        insert_statements = parse_insert_statements(sql_content)
        
        print(f"找到 {len(insert_statements)} 个表的数据:")
        for table_name, data_list in insert_statements.items():
            print(f"  - {table_name}: {len(data_list)} 条记录")
        
        # 按依赖顺序插入数据
        table_order = [
            'alembic_version',
            'admin_users', 
            'users',
            'assets',
            'trades',
            'commission_records',
            'admin_operation_logs',
            'dividend_records',
            'system_configs',
            'commission_settings',
            'distribution_levels',
            'dashboard_stats',
            'distribution_settings',
            'commission_config',
            'user_commission_balance',
            'commission_withdrawals',
            'platform_incomes',
            'short_links',
            'ip_visits',
            'share_messages'
        ]
        
        # 插入数据
        print("5. 插入数据...")
        for table_name in table_order:
            if table_name in insert_statements:
                insert_data(conn, table_name, insert_statements[table_name])
        
        # 插入剩余的表（如果有的话）
        for table_name, data_list in insert_statements.items():
            if table_name not in table_order:
                insert_data(conn, table_name, data_list)
        
        print("6. 验证数据...")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        tables = cursor.fetchall()
        
        print("数据库表及记录数:")
        total_records = 0
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_records += count
            if count > 0:
                print(f"  {table_name}: {count} 条记录")
        
        print(f"\n✓ 数据迁移完成！总共迁移了 {total_records} 条记录")
        
        # 生成迁移摘要
        summary = {
            "migration_date": datetime.now().isoformat(),
            "status": "completed",
            "database_type": "PostgreSQL",
            "total_records": total_records,
            "tables_migrated": len([t for t in tables if cursor.execute(f"SELECT COUNT(*) FROM {t[0]}") or cursor.fetchone()[0] > 0])
        }
        
        with open('postgresql_migration_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print("📄 迁移摘要已保存到: postgresql_migration_summary.json")
        
    except Exception as e:
        print(f"✗ 数据迁移失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()