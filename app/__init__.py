from flask import Flask, request, session, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_babel import Babel, gettext as _
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
    """从 cookie 中获取用户语言偏好，默认英文"""
    return request.cookies.get('language', 'en')

def create_app(config_name='development'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 添加自定义过滤器
    @app.template_filter('number_format')
    def number_format_filter(value):
        try:
            if isinstance(value, (int, float, Decimal)):
                return "{:,.2f}".format(float(value))
            return value
        except (ValueError, TypeError):
            return value
            
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            if value:
                return json.loads(value)
            return []
        except:
            return []
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Eth-Address", "Authorization"]
        }
    })
    
    # 初始化 Babel
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    babel.init_app(app, localeselector=get_locale)
    
    # 设置日志
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('应用启动')
    
    # 注册错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error('Server Error: %s', error)
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    # 注册蓝图
    from .routes import register_blueprints
    register_blueprints(app)
    
    # 初始化存储
    from .utils.storage import init_storage
    if not init_storage(app):
        app.logger.error("七牛云存储初始化失败，应用可能无法正常工作")
        
    return app
