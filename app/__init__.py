from flask import Flask, request, session, jsonify, render_template, current_app
from flask_babel import gettext as _
from app.config import config
import json
import os
import logging
from logging.handlers import RotatingFileHandler
from decimal import Decimal
import click
from flask.cli import with_appcontext
import threading
from app.extensions import db, babel, limiter, scheduler, migrate

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
    from .extensions import init_extensions
    init_extensions(app)
    
    # 设置Babel配置
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    
    # 设置语言选择函数
    def get_locale():
        return request.cookies.get('language', 'en')
    
    babel.locale_selector_func = get_locale
    
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
    
    # 初始化存储（在注册蓝图之前）
    from .utils.storage import init_storage
    if not init_storage(app):
        app.logger.error("存储初始化失败，应用可能无法正常工作")
        raise RuntimeError("存储初始化失败")
    
    # 注册蓝图
    from .routes import register_blueprints
    register_blueprints(app)
    
    # 注册管理员API v2蓝图
    with app.app_context():
        from app.routes.admin_api import register_admin_v2_blueprint
        register_admin_v2_blueprint(app)
    
    # 在生产环境启动交易监控
    if app.config.get('ENV', 'development') == 'production':
        from app.utils.monitor import start_monitor
        start_monitor()
        app.logger.info('交易监控服务已启动')
    
    # 注册初始化分销佣金设置命令
    app.cli.add_command(init_distribution_command)
    
    return app

# 在初始化时添加分销佣金设置
@click.command('init-distribution')
@with_appcontext
def init_distribution_command():
    """初始化分销佣金设置"""
    from app.models.referral import DistributionSetting
    
    # 检查是否已有设置
    existing_settings = DistributionSetting.query.all()
    if existing_settings:
        click.echo('分销佣金设置已存在，跳过初始化')
        return
    
    # 创建初始设置
    settings = [
        DistributionSetting(level=1, commission_rate=0.3),  # 一级分销：30%
        DistributionSetting(level=2, commission_rate=0.15), # 二级分销：15%
        DistributionSetting(level=3, commission_rate=0.05)  # 三级分销：5%
    ]
    
    for setting in settings:
        db.session.add(setting)
    
    db.session.commit()
    click.echo('分销佣金设置初始化完成')
