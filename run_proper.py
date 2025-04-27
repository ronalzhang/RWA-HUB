#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RWA-HUB应用启动器
使用正确的方式启动Flask应用
"""

import os
import sys
import logging
from waitress import serve

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入应用 - 明确导入create_app函数并调用它
from app import create_app

# 创建Flask应用实例
application = create_app()

if __name__ == '__main__':
    # 服务器配置
    port = int(os.environ.get('PORT', 9000))  # 默认使用9000端口
    host = '0.0.0.0'  # 允许外部访问
    
    print("已加载环境变量文件:", os.path.join(current_dir, 'app/.env'))
    print("启动服务器...")
    print("访问地址:")
    print(f"本地:    http://127.0.0.1:{port}")
    print(f"局域网:  http://<本机IP>:{port}")
    
    # 使用waitress作为生产服务器
    serve(
        application,  # 传递应用实例而不是模块
        host=host,
        port=port,
        threads=8,
        url_scheme='http',
        channel_timeout=300,
        cleanup_interval=30,
        max_request_body_size=1073741824  # 1GB
    ) 