#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复版本的RWA-HUB应用启动脚本
解决了导入顺序问题，确保waitress在顶部导入
"""

import logging
import os
import sys
from waitress import serve
from sqlalchemy.exc import OperationalError
from flask_migrate import upgrade

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

# 创建app实例前的准备工作
def verify_db_tables():
    """验证数据库表是否存在"""
    from app import create_app, db
    from app.models import User, Asset, Trade
    
    logging.info("检查数据库表...")
    app = create_app(os.getenv('FLASK_ENV') or 'development')
    
    with app.app_context():
        try:
            # 尝试创建一个临时app上下文，然后查询用户表来验证连接
            user_count = db.session.query(User).count()
            logging.info(f"数据库连接成功，发现 {user_count} 个用户")
            
            # 检查其他关键表是否存在
            try:
                asset_count = db.session.query(Asset).count()
                trade_count = db.session.query(Trade).count()
                logging.info(f"资产表: {asset_count} 条记录")
                logging.info(f"交易表: {trade_count} 条记录")
            except Exception as e:
                logging.warning(f"查询其他表时出错: {str(e)}")
            
            # 获取所有表名
            all_tables = db.inspect(db.engine).get_table_names()
            logging.info(f"数据库中存在的表: {', '.join(all_tables)}")
            
            # 检查关键表是否缺失
            expected_tables = ['users', 'assets', 'trades', 'transactions', 'dividends']
            missing_tables = [table for table in expected_tables if table not in all_tables]
            
            if missing_tables:
                logging.warning(f"警告: 以下关键表缺失: {', '.join(missing_tables)}")
                return False
            
            return True
            
        except OperationalError as e:
            logging.error(f"数据库连接失败: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"验证数据库表时发生未知错误: {str(e)}")
            return False

def init_db():
    """初始化数据库"""
    logging.info("准备初始化数据库...")
    
    # 检查数据库URL是否已设置
    if not os.environ.get('DATABASE_URL'):
        default_db_url = 'sqlite:///app.db'
        logging.warning(f"DATABASE_URL环境变量未设置，使用默认值: {default_db_url}")
        os.environ['DATABASE_URL'] = default_db_url
    
    db_url = os.environ.get('DATABASE_URL')
    logging.info(f"数据库URL: {db_url}")
    
    # 尝试连接数据库
    try:
        # 导入应用
        from app import create_app
        
        app = create_app(os.getenv('FLASK_ENV') or 'development')
        
        # 数据库迁移
        logging.info("执行数据库迁移...")
        with app.app_context():
            upgrade()
            logging.info("数据库迁移完成")
        
        return True
    except Exception as e:
        logging.error(f"数据库初始化失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 记录环境信息
    logging.info(f"Python版本: {sys.version}")
    logging.info(f"运行环境: {os.getenv('FLASK_ENV') or 'development'}")
    logging.info(f"数据库URL: {os.getenv('DATABASE_URL', '未设置')}")
    
    # 初始化数据库
    if os.getenv('SKIP_DB_INIT') != 'true':
        init_db()
    else:
        logging.info("跳过数据库初始化 (SKIP_DB_INIT=true)")
    
    # 验证数据库表
    verify_db_tables()
    
    # 导入创建app函数
    from app import create_app
    
    # 创建Flask应用
    flask_app = create_app(os.getenv('FLASK_ENV') or 'development')
    
    # 服务器设置
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    threads = int(os.getenv('THREADS', 4))
    
    logging.info(f"启动服务器 waitress，监听 {host}:{port}，线程数: {threads}")
    
    # 使用waitress启动应用
    serve(
        flask_app,
        host=host,
        port=port,
        threads=threads,
        channel_timeout=300,
        connection_limit=1000,
        cleanup_interval=30,
        url_scheme='http'
    ) 