import sys
import os
from datetime import datetime

# 设置路径以找到应用
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from alembic import command
from alembic.config import Config

def create_migration(message):
    """创建数据库迁移"""
    # 创建Flask应用
    app = create_app()
    
    with app.app_context():
        # 获取Alembic配置
        alembic_cfg = Config("migrations/alembic.ini")
        alembic_cfg.set_main_option("script_location", "migrations")
        
        # 创建迁移
        command.revision(alembic_cfg, message=message, autogenerate=True)
        
        print(f"已创建迁移: {message}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python create_migration.py '迁移说明'")
        sys.exit(1)
        
    message = sys.argv[1]
    create_migration(message) 