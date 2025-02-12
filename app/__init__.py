from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_babel import Babel
from app.config import config
import json
import os
import logging
from logging.handlers import RotatingFileHandler
from decimal import Decimal

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
babel = Babel()

def get_locale():
    # 从 cookie 中获取用户语言偏好，默认英文
    return request.cookies.get('language', 'en')

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # 加载配置
    if isinstance(config_name, str):
        config_class = config.get(config_name.lower(), config['default'])
        app.config.from_object(config_class)
        # 初始化配置
        config_class.init_app(app)
    else:
        app.config.from_object(config_name)
    
    # 配置 Babel
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'zh_Hant']
    babel.init_app(app)
    
    # 添加安全头
    @app.after_request
    def add_security_headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src * 'self' data: blob: http: https:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com;"
        return response
    
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # 设置日志处理器
    file_handler = RotatingFileHandler(
        'logs/rwa_hub.log',
        maxBytes=10240,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('RWA-HUB 启动')
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)

    # 初始化七牛云存储
    from .utils.storage import init_storage
    with app.app_context():
        init_storage()
    
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
    from .routes import main_bp, auth_bp, assets_bp, api_bp, admin_bp, admin_api_bp, assets_api_bp
    
    # 先注册API路由
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
    app.register_blueprint(assets_api_bp, url_prefix='/api/assets')
    
    # 再注册页面路由
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(assets_bp, url_prefix='/assets')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    return app
