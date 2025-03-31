from flask import Blueprint

# 创建蓝图
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
auth_api_bp = Blueprint('auth_api', __name__)
assets_api_bp = Blueprint('assets_api', __name__, url_prefix='/api/assets')
trades_api_bp = Blueprint('trades_api', __name__)
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')
service_bp = Blueprint('service', __name__, url_prefix='/api/service')

# 添加新的代理蓝图，用于处理外部资源代理
proxy_bp = Blueprint('proxy', __name__, url_prefix='/proxy')

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
    # 注册所有蓝图
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(assets_api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(service_bp)
    app.register_blueprint(proxy_bp)  # 注册代理蓝图
    
    # 注册全局URL前缀修正处理器
    register_global_handlers(app)
    app.logger.info('已注册全局URL前缀修正处理器') 