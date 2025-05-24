"""
管理后台模块化重构
- 将原来4200+行的admin.py拆分为多个专业模块
- 统一认证装饰器和权限管理
- 优化代码结构和可维护性
"""

from flask import Blueprint

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

# 导入所有子模块，确保路由被注册
from . import auth
from . import assets  
from . import users
from . import dashboard
from . import commission
from . import trades
from . import utils

# 导出常用函数，保持向后兼容
from .auth import admin_required, api_admin_required, admin_page_required, permission_required
from .utils import is_admin, has_permission, get_admin_role, get_admin_info, is_valid_solana_address 