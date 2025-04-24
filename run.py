import logging
import os
from app import create_app, db
from sqlalchemy.exc import OperationalError
from flask_migrate import upgrade
from waitress import serve

# 配置详细的日志格式
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def verify_db_tables():
    """验证数据库表是否存在"""
    try:
        temp_app = create_app(os.getenv('FLASK_ENV', 'production'))  # 默认使用生产环境
        with temp_app.app_context():
            # 检查所有模型的表是否存在
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            logger.info(f"现有的数据库表: {existing_tables}")
            
            # 获取所有模型类
            required_tables = {table.name for table in db.Model.metadata.tables.values()}
            logger.info(f"需要的表: {required_tables}")
            
            if not required_tables.issubset(set(existing_tables)):
                missing_tables = required_tables - set(existing_tables)
                logger.warning(f"缺少必要的表: {missing_tables}")
                return False
                
            # 检查每个表的列
            for table_name in required_tables:
                columns = inspector.get_columns(table_name)
                logger.info(f"表 {table_name} 的列: {[col['name'] for col in columns]}")
                
            return True
    except Exception as e:
        logger.error(f"验证数据库表时出错: {e}")
        return False

def init_db():
    """初始化数据库"""
    try:
        # 确保使用正确的配置
        if not os.environ.get('DATABASE_URL'):
            raise ValueError("DATABASE_URL 环境变量未设置")
            
        temp_app = create_app(os.getenv('FLASK_ENV', 'production'))  # 默认使用生产环境
        with temp_app.app_context():
            # 检查数据库连接
            try:
                db.engine.connect()
                logger.info("数据库连接成功")
                logger.info(f"当前数据库 URL: {temp_app.config['SQLALCHEMY_DATABASE_URI']}")
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                raise
            
            # 禁用数据库迁移，避免因找不到迁移版本而导致应用程序不断重启
            # 如需手动迁移，请使用 flask db upgrade 命令
            logger.info("已禁用自动数据库迁移，确保数据库结构已是最新")
            
            # 如果需要创建表，请使用下面的代码
            # db.create_all()
            # logger.info("数据库表已创建")
            
            return True
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e}")
        raise

# 创建全局应用实例
flask_app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    logger.info("启动应用...")
    logger.info(f"环境: {os.environ.get('FLASK_ENV', 'production')}")
    logger.info(f"数据库 URL: {os.environ.get('DATABASE_URL', '未设置')}")
    
    success = False
    
    for attempt in range(3):
        try:
            init_db()
            success = True
            logger.info("数据库初始化成功")
            break
        except Exception as e:
            logger.error(f"第 {attempt + 1} 次尝试初始化数据库失败: {e}")
    
    if not success:
        logger.error("所有数据库初始化尝试都失败了")
    
    # 生产环境配置
    flask_app.config['DEBUG'] = False
    flask_app.config['PROPAGATE_EXCEPTIONS'] = True
    
    port = int(os.environ.get('PORT', 9000))
    host = '0.0.0.0'  # 允许外部访问
    
    print("启动服务器...")
    print("访问地址:")
    print(f"本地:    http://127.0.0.1:{port}")
    print(f"局域网:  http://<本机IP>:{port}")
    
    # 使用waitress作为生产服务器，增加配置选项
    serve(flask_app, 
          host=host, 
          port=port, 
          threads=8,  # 增加线程数
          url_scheme='http',  # 修改为http
          channel_timeout=300,  # 增加超时时间
          cleanup_interval=30,  # 清理间隔
          max_request_body_size=1073741824  # 最大请求体大小（1GB）
    ) 