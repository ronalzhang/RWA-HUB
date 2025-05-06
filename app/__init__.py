import os
import json
import click
import logging
import threading
from decimal import Decimal
from flask import Flask, g, request, session, jsonify, render_template, current_app
from flask_babel import gettext as _
from flask.cli import with_appcontext
from app.extensions import db, babel, limiter, scheduler, migrate, cors, configure_logging
from pathlib import Path
from app.config import config
from logging.handlers import RotatingFileHandler

def create_app(config_name='development'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # -- 修改：根据数据库配置设置速率限制存储URL --
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
        app.config['RATELIMIT_STORAGE_URL'] = db_uri
        app.logger.info(f"设置 Flask-Limiter 存储 URL: {db_uri}")
    else:
        app.logger.warning("未找到数据库 URI，Flask-Limiter 将使用内存存储")
    
    # 配置静态文件
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用静态文件缓存
    app.static_folder = 'static'  # 设置静态文件夹
    app.static_url_path = '/static'  # 设置静态文件URL前缀
    
    # 确保上传目录存在
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        app.logger.info(f'创建上传目录: {uploads_dir}')
    
    # 初始化日志
    configure_logging(app)
    
    # 添加自定义过滤器
    @app.template_filter('number_format')
    def number_format_filter(value, field_name=None):
        """格式化数字，根据字段名决定精度"""
        try:
            if isinstance(value, (int, float, Decimal)):
                # 根据字段名确定格式化精度
                if field_name:
                    # 代币价格: 6位小数
                    if 'token_price' in field_name or 'price' in field_name:
                        return "{:,.6f}".format(float(value))
                    # 面积、总价值、年收益: 2位小数
                    elif any(field in field_name for field in ['area', 'total_value', 'annual_revenue']):
                        return "{:,.2f}".format(float(value))
                    # 代币供应量、剩余供应量: 0位小数
                    elif any(field in field_name for field in ['token_supply', 'remaining_supply']):
                        # 检查是否为整数或可以无损转换为整数
                        float_value = float(value)
                        if float_value == int(float_value):
                            return "{:,}".format(int(float_value))
                        else:
                            # 对于非整数的供应量（理论上不应该，但做兼容处理），保留2位小数
                            return "{:,.2f}".format(float_value)
                
                # 如果没有提供字段名或不匹配任何规则，使用默认格式化
                # 检查是否为整数或可以无损转换为整数
                float_value = float(value)
                if float_value == int(float_value):
                    return "{:,}".format(int(float_value))
                else:
                    # 默认保留2位小数
                    return "{:,.2f}".format(float_value)
            
            # 如果输入不是数字类型，直接返回原值
            return value
        except (ValueError, TypeError) as e:
            app.logger.error(f"格式化数字出错 (field: {field_name}, value: {value}): {str(e)}")
            return value # 出错时返回原值
            
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            if value:
                return json.loads(value)
            return []
        except:
            return []
    
    # 初始化扩展
    from .extensions import init_extensions, bind_db_to_app
    init_extensions(app)
    
    # 确保SQLAlchemy模型绑定到应用上下文
    bind_db_to_app(app)
    
    # 设置Babel配置
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    app.config['LANGUAGES'] = ['en']  # 只使用英文
    
    # 设置语言选择函数，总是返回英文
    def get_locale():
        # 强制使用英文
        g.locale = 'en'
        return 'en'
    
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
    
    # 导入任务处理模块，确保异步任务处理器启动
    with app.app_context():
        import app.tasks
    
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
