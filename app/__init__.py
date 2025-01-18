from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from config import config
import json
import os
from decimal import Decimal

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # 加载配置
    if isinstance(config_name, str):
        app.config.from_object(f'config.{config_name.capitalize()}Config')
    else:
        app.config.from_object(config_name)
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # 添加自定义过滤器
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value) if value else []
        except:
            return []
            
    @app.template_filter('number_format')
    def number_format_filter(value):
        if value is None:
            return '0'
        if isinstance(value, (int, float, Decimal)):
            return "{:,.2f}".format(float(value))
        return value
    
    # 注册蓝图
    from .routes import main_bp, auth_bp, assets_bp, api_bp, admin_bp, admin_api_bp
    
    # 先注册API路由
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
    
    # 再注册页面路由
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(assets_bp, url_prefix='/assets')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    return app