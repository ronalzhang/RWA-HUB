from flask import Blueprint

# 创建蓝图
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# API蓝图
api_bp = Blueprint('api', __name__)
auth_api_bp = Blueprint('auth_api', __name__)
assets_api_bp = Blueprint('assets_api', __name__, url_prefix='/api/assets')
trades_api_bp = Blueprint('trades_api', __name__)
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

# 导入视图函数
from . import main
from . import views
from . import api
from . import admin
from . import assets

# 导入全局处理器
from .assets import register_global_handlers

# 确保所有路由都已注册
from .main import *
from .views import *
from .api import *
from .admin import *
from .assets import *

# 注册蓝图函数
def register_blueprints(app):
    # 注册所有蓝图
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(assets_api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
    
    # 注册全局URL前缀修正处理器
    register_global_handlers(app)
    app.logger.info('已注册全局URL前缀修正处理器')
