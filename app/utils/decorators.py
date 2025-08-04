"""
统一装饰器
提供统一的错误处理、权限验证等装饰器
"""

import functools
import logging
from datetime import datetime
from flask import jsonify, request, g, current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.exceptions import BadRequest
from typing import Callable, Any, Dict, Optional
import traceback

from app.utils.validation_utils import ValidationError

logger = logging.getLogger(__name__)


def handle_api_errors(f: Callable) -> Callable:
    """
    统一的API错误处理装饰器
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"验证错误 - {request.endpoint}: {e.message}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'validation',
                    'message': e.message,
                    'field': e.field,
                    'code': e.code or 'VALIDATION_ERROR'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        except IntegrityError as e:
            logger.error(f"数据完整性错误 - {request.endpoint}: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'integrity',
                    'message': '数据完整性约束违反',
                    'code': 'INTEGRITY_ERROR'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        except SQLAlchemyError as e:
            logger.error(f"数据库错误 - {request.endpoint}: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'database',
                    'message': '数据库操作失败',
                    'code': 'DATABASE_ERROR'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 500
        except BadRequest as e:
            logger.warning(f"请求错误 - {request.endpoint}: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'bad_request',
                    'message': '请求格式错误',
                    'code': 'BAD_REQUEST'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        except PermissionError as e:
            logger.warning(f"权限错误 - {request.endpoint}: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'permission',
                    'message': '权限不足',
                    'code': 'PERMISSION_DENIED'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 403
        except Exception as e:
            logger.error(f"未知错误 - {request.endpoint}: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'internal',
                    'message': '服务器内部错误',
                    'code': 'INTERNAL_ERROR'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    return decorated_function


def require_wallet_address(f: Callable) -> Callable:
    """
    要求钱包地址的装饰器
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # 从多个来源获取钱包地址
        wallet_address = None
        
        # 1. 从请求头获取
        wallet_address = request.headers.get('X-Wallet-Address')
        
        # 2. 从请求参数获取
        if not wallet_address:
            wallet_address = request.args.get('wallet_address')
        
        # 3. 从POST数据获取
        if not wallet_address and request.is_json:
            data = request.get_json(silent=True)
            if data:
                wallet_address = data.get('wallet_address')
        
        # 4. 从表单数据获取
        if not wallet_address and request.form:
            wallet_address = request.form.get('wallet_address')
        
        if not wallet_address:
            logger.warning(f"请求缺少钱包地址 - {request.endpoint}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'authentication',
                    'message': '未提供钱包地址',
                    'code': 'WALLET_ADDRESS_REQUIRED'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 401
        
        # 存储到g对象中供后续使用
        g.wallet_address = wallet_address
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_admin_wallet(f: Callable) -> Callable:
    """
    要求管理员钱包的装饰器
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        from app.services.authentication_service import AuthenticationService
        
        # 先确保有钱包地址
        wallet_address = getattr(g, 'wallet_address', None)
        if not wallet_address:
            # 尝试从请求中获取
            wallet_address = request.headers.get('X-Wallet-Address')
            if not wallet_address and request.is_json:
                data = request.get_json(silent=True)
                if data:
                    wallet_address = data.get('wallet_address')
        
        if not wallet_address:
            logger.warning(f"管理员验证失败 - 未提供钱包地址 - {request.endpoint}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'authentication',
                    'message': '请先连接钱包并登录',
                    'code': 'AUTH_REQUIRED'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 401
        
        # 验证管理员权限
        auth_service = AuthenticationService()
        if not auth_service.verify_admin_wallet(wallet_address):
            logger.warning(f"管理员权限验证失败 - {wallet_address} - {request.endpoint}")
            return jsonify({
                'success': False,
                'error': {
                    'type': 'permission',
                    'message': '钱包地址未注册为管理员',
                    'code': 'ADMIN_ACCESS_DENIED'
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 403
        
        # 存储管理员地址
        g.admin_address = wallet_address
        
        return f(*args, **kwargs)
    
    return decorated_function


def log_api_call(f: Callable) -> Callable:
    """
    记录API调用的装饰器
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = datetime.utcnow()
        
        # 记录请求信息
        request_info = {
            'endpoint': request.endpoint,
            'method': request.method,
            'url': request.url,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'wallet_address': getattr(g, 'wallet_address', None),
            'start_time': start_time.isoformat()
        }
        
        logger.info(f"API调用开始: {request_info}")
        
        try:
            result = f(*args, **kwargs)
            
            # 记录成功信息
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"API调用成功: {request.endpoint} - 耗时: {duration:.3f}s")
            
            return result
        except Exception as e:
            # 记录错误信息
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"API调用失败: {request.endpoint} - 耗时: {duration:.3f}s - 错误: {str(e)}")
            raise
    
    return decorated_function


def validate_json_request(required_fields: Optional[list] = None) -> Callable:
    """
    验证JSON请求的装饰器
    
    Args:
        required_fields: 必填字段列表
        
    Returns:
        装饰器函数
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': {
                        'type': 'validation',
                        'message': '请求必须是JSON格式',
                        'code': 'JSON_REQUIRED'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': {
                        'type': 'validation',
                        'message': '请求体不能为空',
                        'code': 'EMPTY_REQUEST_BODY'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
            
            # 验证必填字段
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or data[field] is None or data[field] == '':
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': {
                            'type': 'validation',
                            'message': f'缺少必填字段: {", ".join(missing_fields)}',
                            'code': 'MISSING_REQUIRED_FIELDS',
                            'missing_fields': missing_fields
                        },
                        'timestamp': datetime.utcnow().isoformat()
                    }), 400
            
            # 将验证后的数据存储到g对象中
            g.json_data = data
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def rate_limit(max_requests: int = 100, window_seconds: int = 3600) -> Callable:
    """
    简单的速率限制装饰器
    
    Args:
        max_requests: 最大请求次数
        window_seconds: 时间窗口（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里可以实现基于Redis或内存的速率限制
            # 为了简化，暂时跳过实际的速率限制逻辑
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def cache_response(timeout: int = 300) -> Callable:
    """
    缓存响应的装饰器
    
    Args:
        timeout: 缓存超时时间（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里可以实现基于Redis的响应缓存
            # 为了简化，暂时跳过实际的缓存逻辑
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def measure_performance(f: Callable) -> Callable:
    """
    性能测量装饰器
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = datetime.utcnow()
        
        try:
            result = f(*args, **kwargs)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # 记录性能指标
            if duration > 2.0:  # 超过2秒的请求记录警告
                logger.warning(f"慢查询警告: {request.endpoint} - 耗时: {duration:.3f}s")
            else:
                logger.debug(f"性能指标: {request.endpoint} - 耗时: {duration:.3f}s")
            
            return result
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"性能测量 - 函数执行失败: {request.endpoint} - 耗时: {duration:.3f}s - 错误: {str(e)}")
            raise
    
    return decorated_function


# 组合装饰器，常用的装饰器组合
def api_endpoint(require_wallet: bool = False, 
                require_admin: bool = False,
                required_fields: Optional[list] = None,
                log_calls: bool = True,
                measure_perf: bool = True) -> Callable:
    """
    API端点组合装饰器
    
    Args:
        require_wallet: 是否需要钱包地址
        require_admin: 是否需要管理员权限
        required_fields: JSON请求的必填字段
        log_calls: 是否记录API调用
        measure_perf: 是否测量性能
        
    Returns:
        装饰器函数
    """
    def decorator(f: Callable) -> Callable:
        # 按顺序应用装饰器
        decorated = f
        
        # 1. 错误处理（最外层）
        decorated = handle_api_errors(decorated)
        
        # 2. 性能测量
        if measure_perf:
            decorated = measure_performance(decorated)
        
        # 3. API调用日志
        if log_calls:
            decorated = log_api_call(decorated)
        
        # 4. JSON验证
        if required_fields:
            decorated = validate_json_request(required_fields)(decorated)
        
        # 5. 管理员权限验证
        if require_admin:
            decorated = require_admin_wallet(decorated)
        
        # 6. 钱包地址验证
        if require_wallet:
            decorated = require_wallet_address(decorated)
        
        return decorated
    
    return decorator