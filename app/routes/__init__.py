from flask import Blueprint

# 创建蓝图
main_bp = Blueprint('main', __name__)
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

# API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
assets_api_bp = Blueprint('assets_api', __name__, url_prefix='/api/assets')
service_bp = Blueprint('service', __name__, url_prefix='/api/service')

# 添加新的代理蓝图，用于处理外部资源代理
proxy_bp = Blueprint('proxy', __name__, url_prefix='/proxy')

# 添加管理员测试蓝图
from .admin_test import admin_test_bp

# 导入视图函数
from . import main
from . import views
from . import api
from . import assets
from . import service
from . import proxy

# 导入全局处理器
from .assets import register_global_handlers

# 导入Solana API
from .solana_api import solana_api as solana_api_bp

# 导入新的模块化admin系统
from .admin import admin_bp, admin_api_bp

# 导入监控管理
from .admin.monitoring import monitoring_bp

# 导入IP统计管理
from .admin.ip_stats import ip_stats_bp

# 导入支付管理
# 支付管理模块
from .admin.payment_management import payment_management_bp

# 资产管理功能已合并到admin/__init__.py中

# 导入分红管理
from .dividend import bp as dividend_bp

# 导入语言切换API
from .language_api import language_api

# 导入健康检查API
from .health_api import health_bp

# 导入交易历史API
from .trades_api import trades_api_bp

# 注册蓝图到app
def register_blueprints(app):
    """初始化所有路由"""
    # 注册主蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(assets_bp)
    
    # 注册新的模块化admin蓝图
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
    
    # 注册监控管理蓝图
    app.register_blueprint(monitoring_bp)

    # 注册IP统计管理蓝图
    app.register_blueprint(ip_stats_bp)
    
    # 注册支付管理蓝图
    # 注册支付管理蓝图
    app.register_blueprint(payment_management_bp, url_prefix='/admin')

    # 资产管理功能已合并到admin蓝图中，不需要单独注册
    
    # 注册分红管理蓝图
    app.register_blueprint(dividend_bp)

    # 注册语言切换API蓝图
    app.register_blueprint(language_api)

    # 注册健康检查API蓝图
    app.register_blueprint(health_bp)
    
    # 注册API蓝图
    app.register_blueprint(api_bp)
    app.register_blueprint(assets_api_bp)
    app.register_blueprint(service_bp)
    
    # V2交易API已整合到主API蓝图中
    
    # 注册交易历史API蓝图
    app.register_blueprint(trades_api_bp)
    
    # 注册代理蓝图
    app.register_blueprint(proxy_bp)
    
    # 注册管理员测试蓝图
    app.register_blueprint(admin_test_bp)
    
    # 注册Solana API蓝图
    app.register_blueprint(solana_api_bp)

    # 导入新闻热点管理蓝图
    from .admin.news_hotspot import news_hotspot_api_bp
    app.register_blueprint(news_hotspot_api_bp)

    # 注册SPL Token API蓝图
    from .spl_token_routes import spl_token_bp
    app.register_blueprint(spl_token_bp)

    # 注册系统配置管理蓝图 - 临时禁用以解决端点冲突
    # from .system_config_routes import system_config_bp
    # app.register_blueprint(system_config_bp)

    # 注册全局处理器
    register_global_handlers(app)
    app.logger.info('已注册全局URL前缀修正处理器')

    app.logger.info("所有路由已注册（使用新模块化admin系统）")