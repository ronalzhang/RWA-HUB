"""
管理后台模块化重构
- 将原来4200+行的admin.py拆分为多个专业模块
- 统一认证装饰器和权限管理
- 优化代码结构和可维护性
"""

from flask import Blueprint, render_template, redirect, url_for

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

# 添加V2版本的页面路由（这些路由在各个专门模块中没有定义）
@admin_bp.route('/v2')
@admin_page_required
def admin_v2_index():
    """V2版本管理后台首页"""
    return render_template('admin_v2/dashboard.html')

@admin_bp.route('/v2/dashboard')
@admin_page_required
def dashboard_v2():
    """V2版本仪表盘页面"""
    return render_template('admin_v2/dashboard.html')

@admin_bp.route('/v2/assets')
@admin_page_required
def assets_v2():
    """V2版本资产管理页面"""
    return render_template('admin_v2/assets.html')

@admin_bp.route('/v2/users')
@admin_page_required
def users_v2():
    """V2版本用户管理页面"""
    return render_template('admin_v2/users.html')

@admin_bp.route('/v2/trades')
@admin_page_required
def trades_v2():
    """V2版本交易管理页面"""
    return render_template('admin_v2/trades.html')

@admin_bp.route('/v2/commission')
@admin_page_required
def commission_v2():
    """V2版本佣金管理页面"""
    return render_template('admin_v2/commission.html')

@admin_bp.route('/v2/settings')
@admin_page_required
def settings_v2():
    """V2版本系统设置页面"""
    return render_template('admin_v2/settings.html')

@admin_bp.route('/v2/admin-users')
@admin_page_required
def admin_users_v2():
    """V2版本管理员用户页面"""
    return render_template('admin_v2/admin_users.html')

# 注意：dashboard、assets、users、trades等路由已在各自模块中定义
# 避免重复定义导致路由冲突 