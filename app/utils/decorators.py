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
from datetime import datetime, timedelta
import time

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'message': '缺少访问令牌', 'authenticated': False}), 401
            
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.current_user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'message': '令牌已过期', 'authenticated': False}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': '无效令牌', 'authenticated': False}), 401
            
        return f(*args, **kwargs)
    return decorated

def eth_address_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        eth_address = None
        
        # 先检查X-Wallet-Address和X-Eth-Address头部
        eth_address = request.headers.get('X-Wallet-Address') or request.headers.get('X-Eth-Address')
        
        # 如果头部中没有，检查Cookie
        if not eth_address:
            eth_address = request.cookies.get('eth_address')
            
        # 如果Cookie中没有，检查URL参数
        if not eth_address:
            eth_address = request.args.get('eth_address')
            
        # 如果URL参数中没有，检查会话
        if not eth_address and 'eth_address' in session:
            eth_address = session['eth_address']

        # 如果没有找到Ethereum地址，返回401
        if not eth_address:
            logging.warning("无法找到钱包地址，访问请求被拒绝")
            return jsonify({'success': False, 'error': '未提供钱包地址', 'authenticated': False}), 401
        
        # 检查地址格式
        if not eth_address.startswith('0x') and len(eth_address) < 30:
            logging.warning(f"无效的钱包地址格式: {eth_address}")
            return jsonify({'success': False, 'error': '无效的钱包地址格式', 'authenticated': False}), 401
            
        # 在g对象中存储Ethereum地址以便视图函数访问
        g.eth_address = eth_address
        g.wallet_address = eth_address  # 为兼容性添加wallet_address
        
        return f(*args, **kwargs)
    return decorated

def wallet_address_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        wallet_address = None
        
        # 记录所有潜在的钱包地址来源，用于调试
        logging.debug("**开始查找钱包地址**")
        logging.debug(f"Headers: {dict(request.headers)}")
        logging.debug(f"Cookies: {request.cookies}")
        logging.debug(f"Args: {request.args}")
        
        # 首先检查X-Wallet-Address和X-Eth-Address头部
        wallet_address = request.headers.get('X-Wallet-Address') or request.headers.get('X-Eth-Address')
        if wallet_address:
            logging.debug(f"从请求头找到钱包地址: {wallet_address}")
        
        # 如果头部中没有，检查Cookie
        if not wallet_address:
            wallet_address = request.cookies.get('wallet_address') or request.cookies.get('eth_address')
            if wallet_address:
                logging.debug(f"从Cookie找到钱包地址: {wallet_address}")
            
        # 如果Cookie中没有，检查URL参数
        if not wallet_address:
            wallet_address = request.args.get('wallet_address') or request.args.get('eth_address')
            if wallet_address:
                logging.debug(f"从URL参数找到钱包地址: {wallet_address}")
            
        # 如果URL参数中没有，检查会话
        if not wallet_address and ('wallet_address' in session or 'eth_address' in session):
            wallet_address = session.get('wallet_address') or session.get('eth_address')
            if wallet_address:
                logging.debug(f"从会话找到钱包地址: {wallet_address}")

        # 如果是POST请求，检查请求体中是否有地址（适用于JSON和表单数据）
        if not wallet_address and request.method == 'POST':
            if request.is_json:
                json_data = request.get_json(silent=True) or {}
                wallet_address = json_data.get('wallet_address') or json_data.get('from_address')
                if wallet_address:
                    logging.debug(f"从JSON请求体找到钱包地址: {wallet_address}")
            elif request.form:
                wallet_address = request.form.get('wallet_address') or request.form.get('eth_address')
                if wallet_address:
                    logging.debug(f"从表单数据找到钱包地址: {wallet_address}")

        # 如果没有找到钱包地址，记录并继续
        if not wallet_address:
            logging.warning("无法找到钱包地址，将继续处理但可能导致部分功能不可用")
            g.wallet_address = None
            g.eth_address = None
            return f(*args, **kwargs)
        
        # 在g对象中存储钱包地址以便视图函数访问
        g.wallet_address = wallet_address
        g.eth_address = wallet_address  # 为兼容性添加eth_address
        logging.info(f"已找到并设置钱包地址: {wallet_address}")
        
        return f(*args, **kwargs)
    return decorated

def api_eth_address_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        eth_address = None
        
        # 先检查X-Wallet-Address和X-Eth-Address头部
        eth_address = request.headers.get('X-Wallet-Address') or request.headers.get('X-Eth-Address')
            
        # 如果没有找到Ethereum地址，返回401
        if not eth_address:
            return jsonify({'success': False, 'error': '未提供钱包地址', 'authenticated': False}), 401
            
        # 在g对象中存储Ethereum地址以便视图函数访问
        g.eth_address = eth_address
        g.wallet_address = eth_address  # 为兼容性添加wallet_address
        
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """管理员权限检查装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        eth_address = None
        
        # 先检查头部
        eth_address = request.headers.get('X-Wallet-Address') or request.headers.get('X-Eth-Address')
        
        # 如果头部中没有，检查Cookie
        if not eth_address:
            eth_address = request.cookies.get('eth_address')
            
        # 如果Cookie中没有，检查URL参数
        if not eth_address:
            eth_address = request.args.get('eth_address')
            
        # 如果URL参数中没有，检查会话
        if not eth_address and 'eth_address' in session:
            eth_address = session['eth_address']

        # 如果没有找到Ethereum地址，返回401
        if not eth_address:
            return jsonify({'success': False, 'error': '未提供钱包地址', 'authenticated': False}), 401
        
        # 检查是否为管理员
        from app.routes.admin import is_admin
        if not is_admin(eth_address):
            logging.warning(f"非管理员尝试访问管理功能: {eth_address}")
            return jsonify({'success': False, 'error': '无权访问，需要管理员权限', 'authenticated': True, 'authorized': False}), 403
            
        # 在g对象中存储Ethereum地址以便视图函数访问
        g.eth_address = eth_address
        g.wallet_address = eth_address  # 为兼容性添加wallet_address
        
        return f(*args, **kwargs)
    return decorated

def api_admin_required(f):
    """API版本的管理员权限装饰器，失败时返回JSON错误而不是重定向"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 记录请求头和参数，帮助调试
        current_app.logger.info(f"API管理员验证 - 请求头: {dict(request.headers)}")
        current_app.logger.info(f"API管理员验证 - 请求参数: {dict(request.args)}")
        
        # 尝试从多个来源获取钱包地址
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.cookies.get('eth_address') or \
                     request.args.get('eth_address') or \
                     session.get('eth_address') or \
                     session.get('admin_eth_address')
        
        # 记录找到的钱包地址
        current_app.logger.info(f"API管理员验证 - 找到的钱包地址: {eth_address}")
                     
        if not eth_address:
            current_app.logger.warning("API管理员验证失败 - 未提供钱包地址")
            return jsonify({'error': '请先连接钱包', 'code': 'AUTH_REQUIRED'}), 401
            
        admin_info = get_admin_permissions(eth_address.lower())
        if not admin_info:
            current_app.logger.warning(f"API管理员验证失败 - 非管理员地址: {eth_address}")
            return jsonify({'error': '您没有管理员权限', 'code': 'ADMIN_REQUIRED'}), 403
            
        g.eth_address = eth_address.lower()
        g.admin_info = admin_info
        current_app.logger.info(f"API管理员验证成功 - 地址: {eth_address}")
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
    """后台任务装饰器，确保任务在后台执行，并记录执行状态"""
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        try:
            # 记录任务开始
            task_name = f.__name__
            logging.info(f"开始执行后台任务 {task_name}")
            
            # 执行实际任务
            result = f(*args, **kwargs)
            
            # 记录成功完成
            end_time = time.time()
            duration = end_time - start_time
            logging.info(f"后台任务 {task_name} 成功完成，耗时 {duration:.2f} 秒")
            
            return result
        except Exception as e:
            # 记录异常
            end_time = time.time()
            duration = end_time - start_time
            logging.error(f"后台任务 {f.__name__} 执行失败，耗时 {duration:.2f} 秒，错误: {str(e)}")
            
            # 重新抛出异常以便上层处理
            raise
    
    return decorated 