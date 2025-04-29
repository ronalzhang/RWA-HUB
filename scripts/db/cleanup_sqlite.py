#!/usr/bin/env python
"""
SQLite清理脚本
检查并删除项目中所有SQLite相关文件和引用，确保应用只使用PostgreSQL。
"""

import os
import glob
import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def cleanup_sqlite():
    """检查并清理SQLite残留文件"""
    print("开始清理SQLite残留...")
    
    # 1. 检查并备份所有.db文件 (SQLite数据库文件)
    sqlite_files = glob.glob(os.path.join(ROOT_DIR, "*.db")) + \
                  glob.glob(os.path.join(ROOT_DIR, "*.db-journal")) + \
                  glob.glob(os.path.join(ROOT_DIR, "*.sqlite")) + \
                  glob.glob(os.path.join(ROOT_DIR, "*.sqlite3"))
    
    if sqlite_files:
        print(f"发现 {len(sqlite_files)} 个SQLite相关文件:")
        for file in sqlite_files:
            print(f"  - {os.path.basename(file)}")
            # 备份并删除
            backup_file = f"{file}.backup"
            try:
                os.rename(file, backup_file)
                print(f"    已备份到 {os.path.basename(backup_file)}")
            except Exception as e:
                print(f"    备份失败: {e}")
    else:
        print("未发现SQLite数据库文件")
    
    # 2. 检查主要配置文件中是否有SQLite配置
    config_files = [
        os.path.join(ROOT_DIR, "app", "config.py"),
        os.path.join(ROOT_DIR, ".env"),
        os.path.join(ROOT_DIR, ".env.example"),
        os.path.join(ROOT_DIR, ".flaskenv")
    ]
    
    print("\n检查配置文件:")
    for config_file in config_files:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                content = f.read().lower()
                if 'sqlite' in content:
                    print(f"  - {os.path.basename(config_file)} 中存在SQLite引用!")
                else:
                    print(f"  - {os.path.basename(config_file)} 清理完成")
    
    # 3. 确认配置中的PostgreSQL正确性
    try:
        sys.path.insert(0, ROOT_DIR)
        from app import create_app, db
        app = create_app()
        with app.app_context():
            url = str(db.engine.url)
            if 'postgresql' in url.lower():
                print(f"\n数据库配置正确: {url}")
            else:
                print(f"\n警告: 数据库URL不是PostgreSQL: {url}")
    except Exception as e:
        print(f"\n检查数据库配置时出错: {e}")
    
    print("\nSQLite清理完成!")
    print("请确保所有迁移脚本和代码都使用的是PostgreSQL语法")

if __name__ == "__main__":
    cleanup_sqlite() 