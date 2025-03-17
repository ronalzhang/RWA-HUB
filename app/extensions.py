from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_babel import Babel
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from apscheduler.schedulers.background import BackgroundScheduler

# 初始化数据库
db = SQLAlchemy()

# 初始化数据库迁移
migrate = Migrate()

# 初始化CORS
cors = CORS()

# 初始化Babel
babel = Babel()

# 初始化请求限制器
limiter = Limiter(key_func=get_remote_address)

# 初始化调度器
scheduler = BackgroundScheduler()

def init_extensions(app):
    """初始化所有扩展"""
    # 初始化数据库
    db.init_app(app)
    
    # 初始化数据库迁移
    migrate.init_app(app, db)
    
    # 初始化CORS
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Eth-Address", "X-Signature"]
        }
    })
    
    # 初始化Babel
    babel.init_app(app)
    
    # 初始化请求限制器
    limiter.init_app(app)
    
    # 初始化调度器（不需要init_app）
    scheduler.start() 