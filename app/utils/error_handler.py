"""
统一错误处理类
提供标准化的错误响应格式和错误日志记录
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from flask import jsonify, request, current_app
from collections import defaultdict
import traceback

logger = logging.getLogger(__name__)


class ErrorHandler:
    """统一错误处理类"""
    
    def __init__(self):
        self.error_codes = {
            # 认证相关错误 (1000-1099)
            'WALLET_NOT_CONNECTED': {
                'code': 1001, 
                'message': '钱包未连接',
                'http_status': 401
            },
            'INVALID_WALLET_ADDRESS': {
                'code': 1002, 
                'message': '无效的钱包地址',
                'http_status': 400
            },
            'AUTH_REQUIRED': {
                'code': 1003, 
                'message': '需要身份验证',
                'http_status': 401
            },
            'ADMIN_ACCESS_DENIED': {
                'code': 1004, 
                'message': '管理员权限不足',
                'http_status': 403
            },
            'TOKEN_EXPIRED': {
                'code': 1005, 
                'message': '令牌已过期',
                'http_status': 401
            },
            'INVALID_TOKEN': {
                'code': 1006, 
                'message': '无效的令牌',
                'http_status': 401
            },
            
            # 验证相关错误 (1100-1199)
            'VALIDATION_ERROR': {
                'code': 1101, 
                'message': '数据验证失败',
                'http_status': 400
            },
            'MISSING_REQUIRED_FIELDS': {
                'code': 1102, 
                'message': '缺少必填字段',
                'http_status': 400
            },
            'INVALID_DATA_FORMAT': {
                'code': 1103, 
                'message': '数据格式错误',
                'http_status': 400
            },
            'JSON_REQUIRED': {
                'code': 1104, 
                'message': '请求必须是JSON格式',
                'http_status': 400
            },
            'EMPTY_REQUEST_BODY': {
                'code': 1105, 
                'message': '请求体不能为空',
                'http_status': 400
            },
            
            # 业务逻辑错误 (1200-1299)
            'INSUFFICIENT_BALANCE': {
                'code': 1201, 
                'message': '余额不足',
                'http_status': 400
            },
            'ASSET_NOT_FOUND': {
                'code': 1202, 
                'message': '资产不存在',
                'http_status': 404
            },
            'TRADE_NOT_FOUND': {
                'code': 1203, 
                'message': '交易记录不存在',
                'http_status': 404
            },
            'USER_NOT_FOUND': {
                'code': 1204, 
                'message': '用户不存在',
                'http_status': 404
            },
            'ASSET_NOT_AVAILABLE': {
                'code': 1205, 
                'message': '资产不可用',
                'http_status': 400
            },
            'INSUFFICIENT_SUPPLY': {
                'code': 1206, 
                'message': '可售数量不足',
                'http_status': 400
            },
            
            # 支付相关错误 (1300-1399)
            'PAYMENT_FAILED': {
                'code': 1301, 
                'message': '支付失败',
                'http_status': 400
            },
            'PAYMENT_TIMEOUT': {
                'code': 1302, 
                'message': '支付超时',
                'http_status': 408
            },
            'INVALID_PAYMENT_AMOUNT': {
                'code': 1303, 
                'message': '无效的支付金额',
                'http_status': 400
            },
            'PAYMENT_ALREADY_PROCESSED': {
                'code': 1304, 
                'message': '支付已处理',
                'http_status': 400
            },
            
            # 区块链相关错误 (1400-1499)
            'BLOCKCHAIN_ERROR': {
                'code': 1401, 
                'message': '区块链操作失败',
                'http_status': 500
            },
            'TRANSACTION_FAILED': {
                'code': 1402, 
                'message': '交易失败',
                'http_status': 400
            },
            'NETWORK_ERROR': {
                'code': 1403, 
                'message': '网络连接错误',
                'http_status': 503
            },
            'CONTRACT_ERROR': {
                'code': 1404, 
                'message': '智能合约错误',
                'http_status': 500
            },
            
            # 系统错误 (1500-1599)
            'DATABASE_ERROR': {
                'code': 1501, 
                'message': '数据库操作失败',
                'http_status': 500
            },
            'INTERNAL_ERROR': {
                'code': 1502, 
                'message': '服务器内部错误',
                'http_status': 500
            },
            'SERVICE_UNAVAILABLE': {
                'code': 1503, 
                'message': '服务暂时不可用',
                'http_status': 503
            },
            'RATE_LIMIT_EXCEEDED': {
                'code': 1504, 
                'message': '请求频率超限',
                'http_status': 429
            },
            
            # 权限相关错误 (1600-1699)
            'PERMISSION_DENIED': {
                'code': 1601, 
                'message': '权限不足',
                'http_status': 403
            },
            'RESOURCE_ACCESS_DENIED': {
                'code': 1602, 
                'message': '资源访问被拒绝',
                'http_status': 403
            },
            'OPERATION_NOT_ALLOWED': {
                'code': 1603, 
                'message': '操作不被允许',
                'http_status': 403
            }
        }
        
        # 错误统计
        self.error_counts = defaultdict(int)
    
    def format_error_response(self, 
                            error_type: str, 
                            message: Optional[str] = None,
                            details: Optional[Dict[str, Any]] = None,
                            field: Optional[str] = None) -> tuple[Dict[str, Any], int]:
        """
        格式化错误响应
        
        Args:
            error_type: 错误类型代码
            message: 自定义错误消息（可选）
            details: 错误详情（可选）
            field: 相关字段名（可选）
            
        Returns:
            tuple: (错误响应字典, HTTP状态码)
        """
        error_info = self.error_codes.get(error_type, {
            'code': 9999,
            'message': '未知错误',
            'http_status': 500
        })
        
        # 使用自定义消息或默认消息
        final_message = message or error_info['message']
        
        # 构建错误响应
        error_response = {
            'success': False,
            'error': {
                'code': error_info['code'],
                'type': error_type,
                'message': final_message,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # 添加可选字段
        if field:
            error_response['error']['field'] = field
        
        if details:
            error_response['error']['details'] = details
        
        # 在开发环境中添加请求信息
        if current_app.debug:
            error_response['error']['request_info'] = {
                'endpoint': request.endpoint,
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr
            }
        
        return error_response, error_info['http_status']
    
    def log_error(self, 
                  error_type: str, 
                  error_message: str, 
                  context: Optional[Dict[str, Any]] = None,
                  exception: Optional[Exception] = None,
                  level: str = 'error') -> None:
        """
        记录错误日志
        
        Args:
            error_type: 错误类型
            error_message: 错误消息
            context: 错误上下文信息
            exception: 异常对象（可选）
            level: 日志级别
        """
        # 更新错误统计
        self.error_counts[error_type] += 1
        
        # 构建日志信息
        log_data = {
            'error_type': error_type,
            'message': error_message,
            'count': self.error_counts[error_type],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 添加请求信息
        if request:
            log_data['request'] = {
                'endpoint': request.endpoint,
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'wallet_address': request.headers.get('X-Wallet-Address', '')
            }
        
        # 添加上下文信息
        if context:
            log_data['context'] = context
        
        # 添加异常信息
        if exception:
            log_data['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc()
            }
        
        # 根据级别记录日志
        log_message = f"错误发生: {error_type} - {error_message}"
        
        if level == 'critical':
            logger.critical(log_message, extra={'error_data': log_data})
        elif level == 'error':
            logger.error(log_message, extra={'error_data': log_data})
        elif level == 'warning':
            logger.warning(log_message, extra={'error_data': log_data})
        else:
            logger.info(log_message, extra={'error_data': log_data})
        
        # 如果错误频率过高，发送告警
        if self.error_counts[error_type] > 10:
            self._send_alert(error_type, self.error_counts[error_type])
    
    def handle_validation_error(self, 
                               field: str, 
                               message: str, 
                               value: Any = None) -> tuple[Dict[str, Any], int]:
        """
        处理验证错误
        
        Args:
            field: 字段名
            message: 错误消息
            value: 字段值（可选）
            
        Returns:
            tuple: (错误响应, HTTP状态码)
        """
        details = {'field': field}
        if value is not None:
            details['value'] = str(value)
        
        self.log_error('VALIDATION_ERROR', f'字段验证失败: {field} - {message}', 
                      context=details, level='warning')
        
        return self.format_error_response('VALIDATION_ERROR', message, details, field)
    
    def handle_business_error(self, 
                            error_type: str, 
                            message: Optional[str] = None,
                            context: Optional[Dict[str, Any]] = None) -> tuple[Dict[str, Any], int]:
        """
        处理业务逻辑错误
        
        Args:
            error_type: 错误类型
            message: 自定义错误消息
            context: 错误上下文
            
        Returns:
            tuple: (错误响应, HTTP状态码)
        """
        self.log_error(error_type, message or self.error_codes.get(error_type, {}).get('message', '业务错误'), 
                      context=context, level='warning')
        
        return self.format_error_response(error_type, message, context)
    
    def handle_system_error(self, 
                          exception: Exception, 
                          error_type: str = 'INTERNAL_ERROR',
                          message: Optional[str] = None) -> tuple[Dict[str, Any], int]:
        """
        处理系统错误
        
        Args:
            exception: 异常对象
            error_type: 错误类型
            message: 自定义错误消息
            
        Returns:
            tuple: (错误响应, HTTP状态码)
        """
        error_message = message or f'系统错误: {str(exception)}'
        
        self.log_error(error_type, error_message, exception=exception, level='error')
        
        # 在生产环境中不暴露具体的系统错误信息
        if not current_app.debug:
            error_message = self.error_codes.get(error_type, {}).get('message', '服务器内部错误')
        
        return self.format_error_response(error_type, error_message)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            dict: 错误统计数据
        """
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_types': dict(self.error_counts),
            'top_errors': sorted(self.error_counts.items(), 
                               key=lambda x: x[1], reverse=True)[:10]
        }
    
    def reset_error_counts(self) -> None:
        """重置错误统计"""
        self.error_counts.clear()
    
    def _send_alert(self, error_type: str, count: int) -> None:
        """
        发送错误告警（内部方法）
        
        Args:
            error_type: 错误类型
            count: 错误次数
        """
        # 这里可以集成邮件、短信、钉钉等告警方式
        logger.critical(f"错误告警: {error_type} 错误次数达到 {count} 次，请及时处理！")
    
    def create_json_response(self, 
                           error_type: str, 
                           message: Optional[str] = None,
                           details: Optional[Dict[str, Any]] = None,
                           field: Optional[str] = None):
        """
        创建JSON错误响应
        
        Args:
            error_type: 错误类型
            message: 自定义错误消息
            details: 错误详情
            field: 相关字段名
            
        Returns:
            Flask Response对象
        """
        error_response, status_code = self.format_error_response(
            error_type, message, details, field
        )
        return jsonify(error_response), status_code


# 全局错误处理器实例
error_handler = ErrorHandler()


def create_error_response(error_type: str, 
                        message: Optional[str] = None,
                        details: Optional[Dict[str, Any]] = None,
                        field: Optional[str] = None):
    """
    便捷函数：创建错误响应
    
    Args:
        error_type: 错误类型
        message: 自定义错误消息
        details: 错误详情
        field: 相关字段名
        
    Returns:
        Flask Response对象
    """
    return error_handler.create_json_response(error_type, message, details, field)


def log_error(error_type: str, 
              error_message: str, 
              context: Optional[Dict[str, Any]] = None,
              exception: Optional[Exception] = None,
              level: str = 'error') -> None:
    """
    便捷函数：记录错误日志
    
    Args:
        error_type: 错误类型
        error_message: 错误消息
        context: 错误上下文信息
        exception: 异常对象
        level: 日志级别
    """
    error_handler.log_error(error_type, error_message, context, exception, level)