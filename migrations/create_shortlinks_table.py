import sys
import os
import datetime
from sqlalchemy import inspect

# 获取项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, ShortLink

# 创建应用上下文
app = create_app()

def create_shortlinks_table():
    """创建短链接表"""
    with app.app_context():
        try:
            # 使用inspect正确检查表是否已存在
            inspector = inspect(db.engine)
            if not inspector.has_table('short_links'):
                print("正在创建 short_links 表...")
                
                # 创建表
                ShortLink.__table__.create(db.engine)
                
                print("short_links 表创建成功")
            else:
                print("short_links 表已存在")
                
        except Exception as e:
            print(f"创建 short_links 表时出错: {e}")
            raise

if __name__ == "__main__":
    create_shortlinks_table() 