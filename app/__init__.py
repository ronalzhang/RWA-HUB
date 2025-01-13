from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # 注册蓝图
    from app.routes import main_bp, auth_bp, assets_bp, admin_bp
    from app.routes import auth_api_bp, assets_api_bp, trades_api_bp, admin_api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(assets_bp, url_prefix='/assets')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_api_bp, url_prefix='/api/auth')
    app.register_blueprint(assets_api_bp, url_prefix='/api/assets')
    app.register_blueprint(trades_api_bp, url_prefix='/api/trades')
    app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
    
    return app