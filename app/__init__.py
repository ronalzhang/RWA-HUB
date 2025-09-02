import os
import json
import click
import logging
import threading
from decimal import Decimal
from flask import Flask, g, request, session, jsonify, render_template, current_app as flask_current_app
from flask_babel import gettext as _
from flask.cli import with_appcontext
from app.extensions import db, babel, limiter, scheduler, migrate, cors, configure_logging
from pathlib import Path
from app.config import config
from logging.handlers import RotatingFileHandler

# 全局应用实例，供其他模块导入
current_app = None
# 全局日志记录器，供其他模块导入
logger = logging.getLogger('app')

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

def create_app(config_name='development'):
    """创建Flask应用实例"""
    global current_app, logger
    app = Flask(__name__)
    
    # 设置全局变量
    current_app = app
    logger = app.logger
    
    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 确保 SECRET_KEY 已设置
    if not app.config.get('SECRET_KEY'):
        app.logger.warning("SECRET_KEY is not set in the configuration file.")
        secret_key_from_env = os.environ.get('SECRET_KEY')
        if secret_key_from_env:
            app.config['SECRET_KEY'] = secret_key_from_env
            app.logger.info("Loaded SECRET_KEY from environment variable.")
        elif config_name == 'development':
            app.config['SECRET_KEY'] = 'dev_secret_key_for_flask_session_testing_only' # 仅用于开发环境
            app.logger.warning("Using a default SECRET_KEY for development. "
                               "Please set a strong, unique SECRET_KEY in your config or environment for production!")
        else:
            app.logger.error("CRITICAL: SECRET_KEY is not set. Application cannot run securely in production without it.")
            raise ValueError("SECRET_KEY must be set for production environments.")
    
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
    
    # -- 修改：在扩展初始化前设置好Limiter的存储URI --
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
        app.config['RATELIMIT_STORAGE_URI'] = db_uri
        app.logger.info(f"设置 Flask-Limiter 存储 URI: {db_uri}")
    else:
        app.logger.warning("未找到数据库 URI，Flask-Limiter 将使用内存存储")

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
    
    # 初始化IP访问追踪中间件
    from app.middleware.ip_tracker import ip_tracker
    ip_tracker.init_app(app)
    app.logger.info("IP访问追踪中间件已初始化")
    
    # 注册蓝图
    from app.routes import register_blueprints
    register_blueprints(app)
    
    # 注册初始化分销佣金设置命令
    app.cli.add_command(init_distribution_command)
    
    # 初始化智能合约监控服务
    try:
        from app.services.contract_monitor import init_contract_monitor
        init_contract_monitor(app)
        app.logger.info("智能合约监控服务已初始化")
    except ImportError as import_error:
        app.logger.warning(f"智能合约监控服务模块导入失败，跳过初始化: {str(import_error)}")
    except Exception as monitor_error:
        app.logger.error(f"初始化智能合约监控服务失败: {str(monitor_error)}")
    
    # 初始化后台任务处理系统
    with app.app_context():
        try:
            # import app.tasks
            app.logger.info("后台任务处理系统已初始化")
            
            # 初始化并启动后台任务调度器
            try:
                from . import tasks
                tasks.start_scheduled_tasks()
            except Exception as task_err:
                app.logger.error(f"启动后台任务调度器失败: {str(task_err)}")
                import traceback
                app.logger.error(traceback.format_exc())
                
        except Exception as e:
            app.logger.error(f"初始化后台任务处理系统失败: {str(e)}")
    
    
    
    return app

    # 确保所有模型都被导入
    with app.app_context():
        # 导入所有模型以确保它们被注册到SQLAlchemy
        from app.models.commission_withdrawal import CommissionWithdrawal
        from app.models.referral import DistributionSetting
        from app.models.commission_config import CommissionConfig, UserCommissionBalance
        app.logger.info("所有模型已导入并注册")

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
