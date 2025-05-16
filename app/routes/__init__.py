from flask import Blueprint

# 创建蓝图
main_bp = Blueprint('main', __name__)
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
assets_api_bp = Blueprint('assets_api', __name__, url_prefix='/api/assets')
trades_api_bp = Blueprint('trades_api', __name__, url_prefix='/api')
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')
service_bp = Blueprint('service', __name__, url_prefix='/api/service')

# 添加新的代理蓝图，用于处理外部资源代理
proxy_bp = Blueprint('proxy', __name__, url_prefix='/proxy')

# 添加管理员测试蓝图
from .admin_test import admin_test_bp

# 导入视图函数
from . import main
from . import views
from . import api
from . import admin
from . import assets
from . import service
from . import proxy

# 导入全局处理器
from .assets import register_global_handlers

# 导入Solana API
from .solana_api import solana_api as solana_api_bp

# 导入Solana管理功能
from .admin_solana import admin_solana_bp

# 注册蓝图到app
def register_blueprints(app):
    """初始化所有路由"""
    # 注册主蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(admin_bp)
    
    # 注册API蓝图
    app.register_blueprint(api_bp)
    app.register_blueprint(assets_api_bp)
    app.register_blueprint(trades_api_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(service_bp)
    
    # 注册代理蓝图
    app.register_blueprint(proxy_bp)
    
    # 注册管理员测试蓝图
    app.register_blueprint(admin_test_bp)
    
    # 注册Solana API蓝图
    app.register_blueprint(solana_api_bp)
    
    # 注册Solana管理功能蓝图
    app.register_blueprint(admin_solana_bp)
    
    # 注册全局处理器
    register_global_handlers(app)
    app.logger.info('已注册全局URL前缀修正处理器')
    
    print("所有路由已注册") 