from flask import Blueprint

# 创建蓝图
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
assets_bp = Blueprint('assets', __name__)
admin_bp = Blueprint('admin', __name__)

# API蓝图
auth_api_bp = Blueprint('auth_api', __name__)
assets_api_bp = Blueprint('assets_api', __name__)
trades_api_bp = Blueprint('trades_api', __name__)
admin_api_bp = Blueprint('admin_api', __name__)

# 导入视图函数
from . import views
from . import api
from . import admin

# 确保所有路由都已注册
from .views import *
from .api import *
from .admin import *
