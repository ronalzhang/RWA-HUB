from gevent import monkey
monkey.patch_all()

import os
import sys
import logging
from multiprocessing import cpu_count
from gunicorn.app.base import BaseApplication
from app import create_app

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# 注意：此文件中的日志记录发生在Flask应用上下文之外，因此使用Python标准日志

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

def main():
    # --- 1. 创建并配置应用 ---
    logging.info("主进程：开始创建Flask应用...")
    flask_app = create_app(os.environ.get('FLASK_CONFIG') or 'production')
    logging.info("主进程：Flask应用创建完成。")

    # --- Gunicorn post_fork 钩子 ---
    def post_fork(server, worker):
        # 在工作进程被创建后，销毁从主进程继承的数据库连接池
        # 这可以防止因连接被意外关闭而导致的 "SSL SYSCALL error: EOF detected" 错误
        # SQLAlchemy 会在需要时为每个工作进程创建新的、独立的连接
        server.log.info(f"Worker {worker.pid} re-initializing database connection pool.")
        with flask_app.app_context():
            from app.extensions import db
            db.engine.dispose()
        server.log.info(f"Worker {worker.pid} database connection pool re-initialized.")

    # --- 2. 记录关键配置（只在主进程执行一次） ---
    with flask_app.app_context():
        # 记录环境变量文件加载状态
        dotenv_path = os.path.join(os.path.dirname(__file__), 'app', '.env')
        if os.path.exists(dotenv_path):
            logging.info(f"主进程：已加载环境变量文件: {dotenv_path}")
        else:
            logging.warning(f"主进程：未找到环境变量文件: {dotenv_path}")

        # 记录数据库连接
        db_uri = flask_app.config.get('SQLALCHEMY_DATABASE_URI')
        logging.info(f"主进程：数据库类型: PostgreSQL - {db_uri}")

        # 记录加密配置加载
        try:
            from app.models.admin import SystemConfig
            from app.utils.crypto_manager import get_crypto_manager
            
            encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
            if encrypted_key:
                logging.info("主进程：✅ 成功加载加密的私钥配置")
            else:
                logging.info("主进程：ℹ️  未找到加密的私钥配置，将使用环境变量中的配置")
        except Exception as e:
            logging.error(f"主进程：❌ 加载加密配置时出错: {e}")

    # --- 3. Gunicorn 服务器配置 ---
    host = os.environ.get('HOST', '0.0.0.0')
    port = os.environ.get('PORT', '9000')
    workers = (cpu_count() * 2) + 1

    options = {
        'bind': f'{host}:{port}',
        'workers': workers,
        'worker_class': 'gevent',
        'timeout': 120,
        'accesslog': '-',
        'errorlog': '-',
        'preload_app': True,
        'post_fork': post_fork, # 在这里注册钩子
    }

    logging.info(f"主进程：🚀 即将启动 Gunicorn，Workers: {workers}, 端口: {port}")
    
    # --- 4. 启动Gunicorn ---
    StandaloneApplication(flask_app, options).run()

if __name__ == '__main__':
    main()