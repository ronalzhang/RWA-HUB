from flask import Blueprint

# 创建蓝图
main_bp = Blueprint('main', __name__)
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

# API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
assets_api_bp = Blueprint('assets_api', __name__, url_prefix='/api/assets')
trades_api_bp = Blueprint('trades_api', __name__, url_prefix='/api/trades')
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

# 导入交易API视图
from . import trades_api

# 导入全局处理器
from .assets import register_global_handlers

# 导入Solana API
from .solana_api import solana_api as solana_api_bp

# 导入Solana管理功能
from .admin_solana import admin_solana_bp

# 导入管理员API兼容路由
from .admin_api import admin_compat_routes_bp, admin_v2_bp, admin_compat_bp, admin_frontend_bp

# 导入新的模块化admin系统
from .admin import admin_bp, admin_api_bp

# 导入佣金配置管理
from .admin.commission_config import commission_config_bp

# 导入IP统计管理
from .admin.ip_stats import ip_stats_bp

# 导入支付管理
from .admin.payment_management import payment_management_bp

# 导入资产管理
from .admin.asset_management import asset_management_bp

# 导入分红管理
from .dividend import bp as dividend_bp

# 导入区块链API
from .blockchain_api import blockchain_bp

# 导入语言切换API
from .language_api import language_api

# 注册蓝图到app
def register_blueprints(app):
    """初始化所有路由"""
    # 注册主蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(assets_bp)
    
    # 注册新的模块化admin蓝图
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
    
    # 注册佣金配置管理蓝图
    app.register_blueprint(commission_config_bp)
    
    # 注册IP统计管理蓝图
    app.register_blueprint(ip_stats_bp)
    
    # 注册支付管理蓝图
    app.register_blueprint(payment_management_bp, url_prefix='/admin')
    
    # 注册资产管理蓝图
    app.register_blueprint(asset_management_bp)
    
    # 注册分红管理蓝图
    app.register_blueprint(dividend_bp)
    
    # 注册区块链API蓝图
    app.register_blueprint(blockchain_bp)
    
    # 注册语言切换API蓝图
    app.register_blueprint(language_api)
    
    # 注册API蓝图
    app.register_blueprint(api_bp)
    app.register_blueprint(assets_api_bp)
    app.register_blueprint(trades_api_bp)
    app.register_blueprint(service_bp)
    
    # 注册代理蓝图
    app.register_blueprint(proxy_bp)
    
    # 注册管理员测试蓝图
    app.register_blueprint(admin_test_bp)
    
    # 注册Solana API蓝图
    app.register_blueprint(solana_api_bp)
    
    # 临时注释掉冲突的蓝图，等重构完成后再启用
    # app.register_blueprint(admin_solana_bp)
    app.register_blueprint(admin_v2_bp)           # 启用V2 API蓝图以支持新的认证系统
    app.register_blueprint(admin_compat_bp)        # 启用兼容路由以支持前端API调用
    app.register_blueprint(admin_compat_routes_bp) # 启用兼容路由以支持前端页面API调用
    app.register_blueprint(admin_frontend_bp)        # 启用前端管理员蓝图
    
    # 注册全局处理器
    register_global_handlers(app)
    app.logger.info('已注册全局URL前缀修正处理器')
    
    print("所有路由已注册（使用新模块化admin系统，临时禁用冲突蓝图）") 