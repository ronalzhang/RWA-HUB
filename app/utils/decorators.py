from functools import wraps
from flask import request, g, jsonify, redirect, url_for, flash, session
import jwt
from app.models.user import User
from eth_utils import is_address
from app.utils.admin import get_admin_permissions

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': '缺少token'}), 401
        
        try:
            data = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
            g.current_user = User.query.get(data['id'])
        except:
            return jsonify({'error': 'token无效或已过期'}), 401
            
        return f(*args, **kwargs)
    return decorated

def eth_address_required(f):
    """要求提供以太坊地址的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     session.get('eth_address')
                     
        if not eth_address:
            flash('请先连接钱包', 'error')
            return redirect(url_for('main.index'))
            
        g.eth_address = eth_address.lower()
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """要求管理员权限的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     session.get('admin_eth_address')
                     
        if not eth_address:
            flash('请先连接钱包', 'error')
            return redirect(url_for('main.index'))
            
        admin_info = get_admin_permissions(eth_address.lower())
        if not admin_info:
            flash('您没有管理员权限', 'error')
            return redirect(url_for('main.index'))
            
        g.eth_address = eth_address.lower()
        g.admin_info = admin_info
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    """要求特定权限的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            eth_address = request.headers.get('X-Eth-Address') or \
                         request.args.get('eth_address') or \
                         session.get('admin_eth_address')
                         
            if not eth_address:
                flash('请先连接钱包', 'error')
                return redirect(url_for('main.index'))
                
            admin_info = get_admin_permissions(eth_address.lower())
            if not admin_info:
                flash('您没有管理员权限', 'error')
                return redirect(url_for('main.index'))
                
            if permission not in admin_info['permissions']:
                flash(f'您没有{permission}权限', 'error')
                return redirect(url_for('admin.index'))
                
            g.eth_address = eth_address.lower()
            g.admin_info = admin_info
            return f(*args, **kwargs)
        return decorated_function
    return decorator 