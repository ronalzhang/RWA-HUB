from flask import Blueprint

# 创建蓝图
main_bp = Blueprint('main', __name__)
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
assets_api_bp = Blueprint('assets_api', __name__, url_prefix='/api/assets')
trades_api_bp = Blueprint('trades_api', __name__)
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')
service_bp = Blueprint('service', __name__)

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
from . import proxy  # 导入代理模块的视图函数

# 导入全局处理器
from .assets import register_global_handlers

# 确保所有路由都已注册
from .main import *
from .views import *
from .api import *
from .admin import *
from .assets import *
from .service import *

# 注册蓝图函数
def register_blueprints(app):
    """注册所有蓝图"""
    from . import views, admin, assets, api, service
    
    # 注册主页蓝图
    app.register_blueprint(views.main_bp)
    
    # 注册管理后台蓝图
    app.register_blueprint(admin.admin_bp, url_prefix='/admin')
    app.register_blueprint(admin.admin_api_bp, url_prefix='/api/admin')
    
    # 注册资产蓝图
    app.register_blueprint(assets.assets_bp, url_prefix='/assets')
    app.register_blueprint(assets.assets_api_bp, url_prefix='/api/assets')
    
    # 注册API蓝图
    app.register_blueprint(api.api_bp, url_prefix='/api')
    
    # 注册服务蓝图
    app.register_blueprint(service.service_bp, url_prefix='/api')
    
    # 注册代理蓝图
    app.register_blueprint(proxy_bp)
    
    # 注册管理员测试蓝图
    app.register_blueprint(admin_test_bp)
    
    # 注册全局URL前缀修正处理器
    register_global_handlers(app)
    app.logger.info('已注册全局URL前缀修正处理器') 