import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # 配置数据库URL
    database_url = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    # 如果是 PostgreSQL URL，需要修改前缀
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # 初始化扩展
    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    
    # 注册蓝图
    from .routes import main_bp, auth_bp, assets_bp, admin_bp
    from .routes.api import auth_api_bp, assets_api_bp, trades_api_bp, admin_api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(admin_bp)
    
    app.register_blueprint(auth_api_bp, url_prefix='/api')
    app.register_blueprint(assets_api_bp, url_prefix='/api')
    app.register_blueprint(trades_api_bp, url_prefix='/api')
    app.register_blueprint(admin_api_bp, url_prefix='/api')
    
    return app