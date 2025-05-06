from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_babel import Babel
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from apscheduler.schedulers.background import BackgroundScheduler
import logging

# 初始化数据库
db = SQLAlchemy()

# 初始化数据库迁移
migrate = Migrate()

# 初始化登录管理器
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'info'

# 初始化JWT
jwt = JWTManager()

# 初始化CORS
cors = CORS()

# 初始化Babel
babel = Babel()

# 初始化请求限制器
limiter = Limiter(key_func=get_remote_address)

# 初始化调度器
scheduler = BackgroundScheduler()

# 添加绑定模型到应用上下文的函数
def bind_db_to_app(app):
    """在应用上下文外也能使用Model.query"""
    with app.app_context():
        from app.models.asset import Asset
        from app.models.user import User
        from app.models.trade import Trade
        from app.models.holding import Holding
        from app.models.dividend import DividendRecord
        from app.models.shortlink import ShortLink
        # 对所有模型进行绑定，确保可以在应用上下文外使用查询
        db.Model.query = db.session.query_property()
    return True

def init_extensions(app):
    """初始化所有扩展"""
    # 初始化数据库
    db.init_app(app)
    
    # 绑定数据库模型到应用
    bind_db_to_app(app)
    
    # 初始化数据库迁移
    migrate.init_app(app, db)
    
    # 初始化CORS
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Eth-Address", "X-Signature", "X-Wallet-Address", 
                             "Authorization", "Access-Control-Allow-Origin", "Origin", "Accept"]
        }
    })
    
    # 初始化Babel
    babel.init_app(app)
    
    # 初始化请求限制器
    storage_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if storage_uri:
        limiter.init_app(app, storage_uri=storage_uri)
        app.logger.info(f"Flask-Limiter 使用数据库存储: {storage_uri}")
    else:
        # 如果没有数据库URI，则使用默认（内存），并保留警告
        limiter.init_app(app)
        app.logger.warning("未配置SQLALCHEMY_DATABASE_URI，Flask-Limiter 将使用内存存储")
    
    # 初始化调度器（不需要init_app）
    try:
        if not scheduler.running:
            scheduler.start()
            app.logger.info("调度器已启动")
        else:
            app.logger.info("调度器已经在运行中")
    except Exception as e:
        app.logger.error(f"启动调度器时出错: {str(e)}")

# 配置日志
def configure_logging(app):
    # 设置日志级别
    app.logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    app.logger.addHandler(console_handler)
    
    app.logger.info("日志系统配置完成") 