import logging
import os
import sys
from waitress import serve
from app import create_app, db
from sqlalchemy.exc import OperationalError
from flask_migrate import upgrade

# 配置详细的日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

def verify_db_tables():
    """验证数据库表是否存在 (增强版)"""
    from app.models import User, Asset, Trade
    logger.info("检查数据库表...")
    try:
        with flask_app.app_context():
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            logger.info(f"现有的数据库表: {existing_tables}")
            
            expected_tables = {'users', 'assets', 'trades', 'transactions', 'dividends'}
            required_tables = {table.name for table in db.Model.metadata.tables.values()}
            logger.info(f"模型定义的表: {required_tables}")
            
            missing_expected = expected_tables - set(existing_tables)
            if missing_expected:
                logger.warning(f"警告: 以下关键表缺失: {', '.join(missing_expected)}")
            
            if not required_tables.issubset(set(existing_tables)):
                missing_tables = required_tables - set(existing_tables)
                logger.warning(f"缺少必要的表: {missing_tables}")
                return False
                
            for table_name in required_tables.intersection(set(existing_tables)):
                columns = inspector.get_columns(table_name)
                logger.info(f"表 {table_name} 的列: {[col['name'] for col in columns]}")
                
            return True
    except OperationalError as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"验证数据库表时发生未知错误: {str(e)}")
        return False

def init_db():
    """初始化数据库"""
    logger.info("准备初始化数据库...")
    try:
        if not os.environ.get('DATABASE_URL'):
            default_db_url = 'postgresql://rwa_hub_user:password@localhost/rwa_hub'
            logger.warning(f"DATABASE_URL环境变量未设置，使用默认值: {default_db_url}")
            os.environ['DATABASE_URL'] = default_db_url
            
        db_url = os.environ.get('DATABASE_URL')
        logger.info(f"数据库URL: {db_url}")
        
        with flask_app.app_context():
            try:
                db.engine.connect()
                logger.info("数据库连接成功")
                logger.info(f"当前数据库 URL: {flask_app.config['SQLALCHEMY_DATABASE_URI']}")
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                raise
            
            logger.info("已禁用自动数据库迁移，确保数据库结构已是最新")
            
            return True
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e}")
        raise

# 创建全局应用实例
flask_app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    logger.info("启动应用...")
    logger.info(f"环境: {os.environ.get('FLASK_ENV', 'production')}")
    logger.info(f"数据库 URL: {flask_app.config.get('SQLALCHEMY_DATABASE_URI', '未设置')}")
    
    success = False
    
    for attempt in range(3):
        try:
            with flask_app.app_context():
                init_db()
            success = True
            logger.info("数据库初始化成功")
            break
        except Exception as e:
            logger.error(f"第 {attempt + 1} 次尝试初始化数据库失败: {e}")
    
    if not success:
        logger.error("所有数据库初始化尝试都失败了")
    
    verify_db_tables()
    
    if not success:
        logger.error("所有数据库初始化尝试都失败了")
    
    # 生产环境配置
    flask_app.config['DEBUG'] = False
    flask_app.config['PROPAGATE_EXCEPTIONS'] = True
    
    port = int(os.environ.get('PORT', 9000))
    host = '0.0.0.0'  # 允许外部访问
    threads = int(os.environ.get('THREADS', 8))
    
    print("启动服务器...")
    print("访问地址:")
    print(f"本地:    http://127.0.0.1:{port}")
    print(f"局域网:  http://<本机IP>:{port}")
    
    serve(flask_app, 
          host=host, 
          port=port, 
          threads=threads,
          url_scheme='http',  # 修改为http
          channel_timeout=300,  # 增加超时时间
          cleanup_interval=30,  # 清理间隔
          max_request_body_size=1073741824  # 最大请求体大小（1GB）
    ) 