#!/usr/bin/env python3
"""
创建分享消息表
运行: python migrations/create_share_messages_table.py
"""

import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.models import db
from app.models.share_message import ShareMessage
from app import create_app

def create_share_messages_table():
    """创建分享消息表"""
    print("开始创建分享消息表...")
    
    try:
        # 创建表
        ShareMessage.__table__.create(db.engine, checkfirst=True)
        print("✓ 分享消息表创建成功")
        
        # 初始化默认数据
        ShareMessage.init_default_messages()
        print("✓ 默认分享消息初始化成功")
        
    except Exception as e:
        print(f"✗ 创建分享消息表失败: {str(e)}")
        raise

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        create_share_messages_table()
        print("分享消息表创建完成！") 