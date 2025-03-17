from functools import wraps
from flask import request, g, jsonify, redirect, url_for, flash, session, current_app
import jwt
from app.models.user import User
from eth_utils import is_address
from app.utils.admin import get_admin_permissions
import threading
from app.extensions import db
import traceback
import logging
from threading import Thread

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
    """要求用户已经连接钱包"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        eth_address = None

        # 检查头部参数
        if 'X-Eth-Address' in request.headers:
            eth_address = request.headers.get('X-Eth-Address')
            if eth_address:
                g.eth_address = eth_address
                current_app.logger.info(f"从请求头获取钱包地址: {eth_address}")
        
        # 检查cookie
        if not eth_address:
            eth_address = request.cookies.get('eth_address')
            if eth_address:
                g.eth_address = eth_address
                current_app.logger.info(f"从cookie获取钱包地址: {eth_address}")
        
        # 检查session
        if not eth_address and 'eth_address' in session:
            eth_address = session['eth_address']
            if eth_address:
                g.eth_address = eth_address
                current_app.logger.info(f"从session获取钱包地址: {eth_address}")
                
        # 如果都没有找到地址，返回错误
        if not eth_address:
            current_app.logger.warning("请求未提供钱包地址")
            return jsonify({'error': '未提供钱包地址', 'code': 403}), 403
            
        return f(*args, **kwargs)
    return decorated_function

def api_eth_address_required(f):
    """API路由要求提供以太坊地址的装饰器，返回JSON响应"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     request.json.get('wallet_address') if request.json else None
        
        current_app.logger.info(f"钱包地址来源:")
        current_app.logger.info(f"- Header: {request.headers.get('X-Eth-Address')}")
        current_app.logger.info(f"- Args: {request.args.get('eth_address')}")
        current_app.logger.info(f"- JSON: {request.json.get('wallet_address') if request.json else None}")
                     
        if not eth_address:
            current_app.logger.warning(f"未提供钱包地址")
            return jsonify({'error': '请先连接钱包', 'code': 'WALLET_REQUIRED'}), 401
            
        # 区分ETH和SOL地址处理
        g.eth_address = eth_address.lower() if eth_address.startswith('0x') else eth_address
        current_app.logger.info(f"最终使用地址: {g.eth_address}")
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

def async_task(f):
    """
    异步任务装饰器，用于将函数放入后台线程执行
    
    使用方法:
    @async_task
    def my_long_task():
        # 耗时操作...
        return result

    my_long_task()  # 会在后台线程中执行
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 获取当前应用上下文
        app = current_app._get_current_object()
        
        def task_wrapper():
            # 创建应用上下文
            with app.app_context():
                try:
                    result = f(*args, **kwargs)
                    return result
                except Exception as e:
                    # 记录异常，但不阻止主线程
                    app.logger.error(f"异步任务出错: {str(e)}")
                    app.logger.error(traceback.format_exc())
                    # 确保数据库回滚，防止连接泄露
                    try:
                        db.session.rollback()
                    except:
                        pass
        
        thread = threading.Thread(target=task_wrapper)
        thread.daemon = True
        thread.start()
        return thread
    
    return wrapper
    
def log_activity(activity_type):
    """记录用户活动的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取当前用户
            user_address = getattr(g, 'eth_address', None)
            
            # 记录活动开始
            if user_address:
                current_app.logger.info(f"用户活动 - {activity_type} - 开始 - 用户: {user_address}")
            
            # 执行被装饰的函数
            result = f(*args, **kwargs)
            
            # 记录活动结束
            if user_address:
                current_app.logger.info(f"用户活动 - {activity_type} - 结束 - 用户: {user_address}")
            
            return result
        return decorated_function
    return decorator 

def task_background(f):
    """后台任务装饰器，用于创建后台线程执行任务"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 获取当前应用上下文
        app = current_app._get_current_object()
        
        def task_wrapper():
            with app.app_context():
                return f(*args, **kwargs)
        
        thread = Thread(target=task_wrapper)
        thread.daemon = True
        thread.start()
        return thread
    return decorated 