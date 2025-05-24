"""
管理员认证模块
统一的认证装饰器和登录相关功能
"""

from flask import (
    render_template, request, redirect, url_for, 
    session, jsonify, current_app, g
)
from functools import wraps
from app.models.admin import AdminUser
from app.utils.decorators import eth_address_required
from app.utils.admin import get_admin_permissions
from sqlalchemy import func
from . import admin_bp, admin_api_bp
from .utils import get_admin_info, is_admin, has_permission


def api_admin_required(f):
    """API版本的管理员权限装饰器，失败时返回JSON错误"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 优先检查session中的安全验证状态
        if session.get('admin_verified') and session.get('admin_wallet_address'):
            wallet_address = session.get('admin_wallet_address')
            admin_user = AdminUser.query.filter(
                func.lower(AdminUser.wallet_address) == wallet_address.lower()
            ).first()
            
            if admin_user:
                g.eth_address = wallet_address
                g.admin = admin_user
                g.admin_user_id = admin_user.id
                g.admin_role = admin_user.role
                current_app.logger.info(f"API管理员验证通过(session) - 管理员ID: {admin_user.id}")
                return f(*args, **kwargs)
        
        # 尝试其他认证方式
        eth_address = (
            request.headers.get('X-Eth-Address') or 
            request.headers.get('X-Wallet-Address') or
            request.cookies.get('eth_address') or 
            request.args.get('eth_address') or 
            session.get('eth_address') or 
            session.get('admin_eth_address')
        )
                     
        if not eth_address:
            return jsonify({'error': '请先连接钱包并登录', 'code': 'AUTH_REQUIRED'}), 401
            
        # 检查管理员权限
        admin_info = get_admin_permissions(eth_address.lower())
        if not admin_info:
            return jsonify({'error': '您没有管理员权限', 'code': 'ADMIN_REQUIRED'}), 403
            
        g.eth_address = eth_address.lower()
        g.admin_info = admin_info
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """页面版本的管理员权限装饰器"""
    @eth_address_required
    def admin_check(*args, **kwargs):
        if not is_admin():
            current_app.logger.warning(f'管理员权限检查失败: {g.eth_address}')
            return redirect(url_for('admin.login_v2'))
        return f(*args, **kwargs)
    return admin_check


def permission_required(permission):
    """特定权限检查装饰器"""
    def decorator(f):
        @admin_required
        def permission_check(*args, **kwargs):
            if not has_permission(permission):
                return jsonify({'error': f'您没有{permission}权限'}), 403
            return f(*args, **kwargs)
        return permission_check
    return decorator


def admin_page_required(f):
    """管理后台页面访问装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查session中的admin验证状态
        if session.get('admin_verified') and session.get('admin_wallet_address'):
            wallet_address = session.get('admin_wallet_address')
            admin_user = AdminUser.query.filter(
                func.lower(AdminUser.wallet_address) == wallet_address.lower()
            ).first()
            
            if admin_user:
                g.admin = admin_user
                g.admin_user_id = admin_user.id
                g.admin_role = admin_user.role
                g.eth_address = wallet_address
                return f(*args, **kwargs)
        
        # 如果验证失败，重定向到登录页面
        return redirect(url_for('admin.login_v2'))
    return decorated_function


# 登录相关路由
@admin_bp.route('/login')
def login():
    """管理员登录 - 重定向到V2版本"""
    return redirect(url_for('admin.login_v2'))


@admin_bp.route('/v2/login')
def login_v2():
    """V2版本管理员登录页面"""
    return render_template('admin/v2/login.html')


@admin_bp.route('/api/check-auth')
def check_auth():
    """检查管理员认证状态API"""
    try:
        if session.get('admin_verified') and session.get('admin_wallet_address'):
            wallet_address = session.get('admin_wallet_address')
            admin_user = AdminUser.query.filter(
                func.lower(AdminUser.wallet_address) == wallet_address.lower()
            ).first()
            
            if admin_user:
                return jsonify({
                    'authenticated': True,
                    'admin': {
                        'id': admin_user.id,
                        'name': admin_user.username or 'Admin',
                        'wallet_address': admin_user.wallet_address,
                        'role': admin_user.role
                    }
                })
        
        return jsonify({'authenticated': False})
        
    except Exception as e:
        current_app.logger.error(f"检查认证状态失败: {str(e)}")
        return jsonify({'authenticated': False, 'error': str(e)}), 500


@admin_bp.route('/api/logout', methods=['POST'])
def logout_api():
    """管理员登出API"""
    session.clear()
    return jsonify({'success': True, 'message': '已成功登出'})


@admin_bp.route('/logout')
def logout():
    """管理员登出"""
    session.clear()
    return redirect(url_for('admin.login_v2'))


# 添加缺失的管理员检查API
@admin_bp.route('/api/check', methods=['GET', 'POST'])
def check_admin():
    """检查钱包地址是否为管理员 - 兼容前端调用"""
    try:
        # 获取钱包地址
        address = None
        if request.method == 'GET':
            address = request.args.get('address')
        else:  # POST
            data = request.get_json() or {}
            address = data.get('address')
        
        if not address:
            return jsonify({'is_admin': False, 'error': '缺少钱包地址'}), 400
        
        # 检查是否为管理员
        admin_user = AdminUser.query.filter(
            func.lower(AdminUser.wallet_address) == address.lower()
        ).first()
        
        if admin_user:
            current_app.logger.info(f"管理员检查通过: {address}")
            return jsonify({
                'is_admin': True,
                'admin_info': {
                    'id': admin_user.id,
                    'name': admin_user.username or 'Admin',
                    'role': admin_user.role
                }
            })
        else:
            current_app.logger.info(f"非管理员地址: {address}")
            return jsonify({'is_admin': False})
            
    except Exception as e:
        current_app.logger.error(f"检查管理员状态失败: {str(e)}")
        return jsonify({'is_admin': False, 'error': str(e)}), 500


# 添加admin_api_bp蓝图的路由，匹配前端期望的/api/admin/check
@admin_api_bp.route('/check', methods=['GET', 'POST'])
def check_admin_api():
    """检查钱包地址是否为管理员 - API蓝图版本"""
    try:
        # 获取钱包地址
        address = None
        if request.method == 'GET':
            address = request.args.get('address')
        else:  # POST
            data = request.get_json() or {}
            address = data.get('address')
        
        if not address:
            return jsonify({'is_admin': False, 'error': '缺少钱包地址'}), 400
        
        # 检查是否为管理员
        admin_user = AdminUser.query.filter(
            func.lower(AdminUser.wallet_address) == address.lower()
        ).first()
        
        if admin_user:
            current_app.logger.info(f"管理员检查通过: {address}")
            return jsonify({
                'is_admin': True,
                'admin_info': {
                    'id': admin_user.id,
                    'name': admin_user.username or 'Admin',
                    'role': admin_user.role
                }
            })
        else:
            current_app.logger.info(f"非管理员地址: {address}")
            return jsonify({'is_admin': False})
            
    except Exception as e:
        current_app.logger.error(f"检查管理员状态失败: {str(e)}")
        return jsonify({'is_admin': False, 'error': str(e)}), 500 