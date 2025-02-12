import logging
import os
import time
from app import create_app, db
from sqlalchemy.exc import OperationalError
from flask_migrate import upgrade
from waitress.adjustments import Adjustments

# 配置详细的日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def wait_for_db(max_retries=5, retry_interval=5):
    """等待数据库就绪"""
    for i in range(max_retries):
        try:
            app = create_app(os.getenv('FLASK_ENV', 'production'))
            with app.app_context():
                db.engine.connect()
                logger.info("数据库连接成功")
                return True
        except Exception as e:
            logger.warning(f"第 {i + 1} 次尝试连接数据库失败: {e}")
            if i < max_retries - 1:
                logger.info(f"等待 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)
    return False

def verify_db_tables():
    """验证数据库表是否存在"""
    try:
        app = create_app(os.getenv('FLASK_ENV', 'production'))
        with app.app_context():
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            required_tables = {table.name for table in db.Model.metadata.tables.values()}
            
            if not required_tables.issubset(set(existing_tables)):
                missing_tables = required_tables - set(existing_tables)
                logger.warning(f"缺少必要的表: {missing_tables}")
                return False
            return True
    except Exception as e:
        logger.error(f"验证数据库表时出错: {e}")
        return False

def init_db():
    """初始化数据库"""
    if not os.environ.get('DATABASE_URL'):
        raise ValueError("DATABASE_URL 环境变量未设置")
        
    if not wait_for_db():
        raise Exception("无法连接到数据库")
        
    app = create_app(os.getenv('FLASK_ENV', 'production'))
    with app.app_context():
        try:
            logger.info("开始运行数据库迁移...")
            upgrade()
            logger.info("数据库迁移完成")
        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            logger.info("尝试直接创建数据库表...")
            db.create_all()
            logger.info("数据库表创建完成")
        
        if not verify_db_tables():
            raise Exception("数据库表验证失败")

def configure_server():
    """配置生产服务器"""
    port = int(os.environ.get('PORT', 10000))
    threads = int(os.environ.get('WAITRESS_THREADS', 8))
    
    return {
        'port': port,
        'threads': threads,
        'host': '0.0.0.0',
        'url_scheme': 'http'
    }

if __name__ == '__main__':
    logger.info("启动应用...")
    logger.info(f"环境: {os.environ.get('FLASK_ENV', 'production')}")
    
    try:
        init_db()
        logger.info("数据库初始化成功")
        
        app = create_app(os.getenv('FLASK_ENV', 'production'))
        app.config['DEBUG'] = False
        app.config['PROPAGATE_EXCEPTIONS'] = True
        
        server_config = configure_server()
        
        print("启动服务器...")
        print("访问地址:")
        print(f"本地: http://127.0.0.1:{server_config['port']}")
        
        from waitress import serve
        serve(app, **server_config)
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise
