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
    
    # 配置上传文件夹
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 创建资产类型子目录
    asset_types = ['real_estate', 'quasi_real_estate']
    for asset_type in asset_types:
        type_dir = os.path.join(app.config['UPLOAD_FOLDER'], asset_type)
        os.makedirs(type_dir, exist_ok=True)
    
    # 初始化扩展
    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    
    # 注册蓝图
    from .routes import main_bp, auth_bp, assets_bp, admin_bp
    from .routes.api import auth_api_bp, assets_api_bp, trades_api_bp
    from .routes.admin import admin_api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(assets_bp, url_prefix='/assets')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    app.register_blueprint(auth_api_bp, url_prefix='/api/auth')
    app.register_blueprint(assets_api_bp, url_prefix='/api/assets')
    app.register_blueprint(trades_api_bp, url_prefix='/api/trades')
    app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
    
    return app