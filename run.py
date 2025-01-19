import logging
import os
from app import create_app, db
from sqlalchemy.exc import OperationalError
from flask_migrate import upgrade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_db_tables():
    """验证数据库表是否存在"""
    try:
        app = create_app(os.getenv('FLASK_ENV', 'production'))  # 默认使用生产环境
        with app.app_context():
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
            
        app = create_app(os.getenv('FLASK_ENV', 'production'))  # 默认使用生产环境
        with app.app_context():
            # 检查数据库连接
            try:
                db.engine.connect()
                logger.info("数据库连接成功")
                logger.info(f"当前数据库 URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                raise
            
            # 运行数据库迁移
            try:
                logger.info("开始运行数据库迁移...")
                upgrade()
                logger.info("数据库迁移完成")
            except Exception as e:
                logger.error(f"数据库迁移失败: {e}")
                # 如果迁移失败，尝试直接创建表
                logger.info("尝试直接创建数据库表...")
                db.create_all()
                logger.info("数据库表创建完成")
            
            # 验证表是否创建成功
            if not verify_db_tables():
                raise Exception("数据库表验证失败")
                
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e}")
        raise

if __name__ == '__main__':
    logger.info("启动应用...")
    logger.info(f"环境: {os.environ.get('FLASK_ENV', 'production')}")  # 默认使用生产环境
    logger.info(f"数据库 URL: {os.environ.get('DATABASE_URL', '未设置')}")
    
    success = False
    
    for attempt in range(3):  # 最多尝试3次
        try:
            init_db()
            success = True
            logger.info("数据库初始化成功")
            break
        except Exception as e:
            logger.error(f"第 {attempt + 1} 次尝试初始化数据库失败: {e}")
    
    if not success:
        logger.error("所有数据库初始化尝试都失败了")
        
    app = create_app(os.getenv('FLASK_ENV', 'production'))  # 默认使用生产环境
    port = int(os.environ.get('PORT', 10000))  # Render 默认使用 10000 端口
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("启动服务器...")
    print("访问地址:")
    print(f"本地:    http://127.0.0.1:{port}")
    print(f"外部:    http://{host}:{port}")
    
    if os.environ.get('FLASK_ENV') == 'production':
        # 生产环境使用 waitress
        from waitress import serve
        serve(app, host=host, port=port)
    else:
        # 开发环境使用 Flask 内置服务器
        app.run(host=host, port=port, debug=debug)