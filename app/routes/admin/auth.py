"""
管理员认证模块 - 修复版本
统一的认证装饰器和登录相关功能
"""

from flask import (
    render_template, request, redirect, url_for, 
    session, jsonify, current_app, g
)
from functools import wraps
from app.models.admin import AdminUser
from app.utils.auth import eth_address_required
from app.utils.admin import is_admin
from app.utils.admin import get_admin_permissions
from app.services.authentication_service import get_auth_service
from sqlalchemy import func
from . import admin_bp, admin_api_bp
from .utils import get_admin_info, has_permission


def api_admin_required(f):
    """API版本的管理员权限装饰器，失败时返回JSON错误"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 优先检查session中的安全验证状态
        if session.get('admin_verified') and session.get('admin_wallet_address'):
            wallet_address = session.get('admin_wallet_address')
            auth_service = get_auth_service()
            if auth_service.verify_admin_wallet(wallet_address):
                g.eth_address = wallet_address
                g.wallet_address = wallet_address
                current_app.logger.info(f"API管理员验证通过(session) - 地址: {wallet_address}")
                return f(*args, **kwargs)
        
        # 尝试其他认证方式
        wallet_address = (
            request.headers.get('X-Eth-Address') or 
            request.headers.get('X-Wallet-Address') or
            request.cookies.get('eth_address') or 
            request.args.get('eth_address') or 
            session.get('eth_address') or 
            session.get('admin_eth_address')
        )
                     
        if not wallet_address:
            current_app.logger.warning("API管理员验证失败 - 未提供钱包地址")
            return jsonify({'error': '请先连接钱包并登录', 'code': 'AUTH_REQUIRED'}), 401
            
        # 使用统一认证服务验证管理员权限
        auth_service = get_auth_service()
        if not auth_service.verify_admin_wallet(wallet_address):
            current_app.logger.warning(f"API管理员验证失败 - 地址: {wallet_address}")
            return jsonify({'error': '您没有管理员权限', 'code': 'ADMIN_REQUIRED'}), 403
            
        # 设置全局变量
        g.eth_address = wallet_address
        g.wallet_address = wallet_address  # 兼容性
        
        current_app.logger.info(f"API管理员验证通过 - 地址: {wallet_address}")
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
            auth_service = get_auth_service()
            if auth_service.verify_admin_wallet(wallet_address):
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
    return render_template('admin_v2/login.html')


@admin_bp.route('/api/check-auth')
def check_auth():
    """检查管理员认证状态API"""
    try:
        if session.get('admin_verified') and session.get('admin_wallet_address'):
            wallet_address = session.get('admin_wallet_address')
            auth_service = get_auth_service()
            admin_info = auth_service.get_admin_info(wallet_address)
            
            if admin_info:
                return jsonify({
                    'authenticated': True,
                    'admin': {
                        'id': admin_info.get('id'),
                        'name': admin_info.get('username', 'Admin'),
                        'wallet_address': admin_info.get('wallet_address'),
                        'role': admin_info.get('role', 'admin')
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
        
        # 使用统一认证服务检查是否为管理员
        auth_service = get_auth_service()
        admin_info = auth_service.get_admin_info(address)
        
        if admin_info:
            current_app.logger.info(f"管理员检查通过: {address}")
            return jsonify({
                'is_admin': True,
                'admin_info': {
                    'id': admin_info.get('id'),
                    'name': admin_info.get('username', 'Admin'),
                    'role': admin_info.get('role', 'admin')
                }
            })
        else:
            current_app.logger.info(f"非管理员地址: {address}")
            return jsonify({'is_admin': False})
            
    except Exception as e:
        current_app.logger.error(f"检查管理员状态失败: {str(e)}")
        return jsonify({'is_admin': False, 'error': str(e)}), 500


# 添加V2版本的认证路由
@admin_api_bp.route('/v2/auth/challenge', methods=['GET'])
def get_challenge():
    """获取认证挑战"""
    import uuid
    nonce = str(uuid.uuid4())
    session['auth_nonce'] = nonce
    return jsonify({'nonce': nonce})


@admin_api_bp.route('/v2/auth/login', methods=['POST'])
def login_v2_api():
    """V2版本管理员登录API"""
    try:
        data = request.get_json() or {}
        wallet_address = data.get('wallet_address')
        signature = data.get('signature')
        message = data.get('message')
        
        if not wallet_address or not signature or not message:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        # 验证nonce
        expected_nonce = session.get('auth_nonce')
        if not expected_nonce or expected_nonce not in message:
            return jsonify({'success': False, 'error': '无效的认证挑战'}), 400
        
        # 验证是否为管理员
        auth_service = get_auth_service()
        admin_info = auth_service.get_admin_info(wallet_address)
        
        if not admin_info:
            current_app.logger.warning(f"非管理员尝试登录: {wallet_address}")
            return jsonify({'success': False, 'error': '您没有管理员权限'}), 403
        
        # 设置session
        session['admin_verified'] = True
        session['admin_wallet_address'] = wallet_address
        session['admin_id'] = admin_info.get('id')
        session['admin_role'] = admin_info.get('role')
        
        # 清除nonce
        session.pop('auth_nonce', None)
        
        current_app.logger.info(f"管理员登录成功: {wallet_address}")
        return jsonify({
            'success': True,
            'admin': {
                'id': admin_info.get('id'),
                'name': admin_info.get('username', 'Admin'),
                'role': admin_info.get('role', 'admin'),
                'wallet_address': wallet_address
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"管理员登录失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
        
        # 使用统一认证服务检查是否为管理员
        auth_service = get_auth_service()
        admin_info = auth_service.get_admin_info(address)
        
        if admin_info:
            current_app.logger.info(f"管理员检查通过: {address}")
            return jsonify({
                'is_admin': True,
                'admin_info': {
                    'id': admin_info.get('id'),
                    'name': admin_info.get('username', 'Admin'),
                    'role': admin_info.get('role', 'admin')
                }
            })
        else:
            current_app.logger.info(f"非管理员地址: {address}")
            return jsonify({'is_admin': False})
            
    except Exception as e:
        current_app.logger.error(f"检查管理员状态失败: {str(e)}")
        return jsonify({'is_admin': False, 'error': str(e)}), 500