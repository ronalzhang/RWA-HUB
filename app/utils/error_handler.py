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

# 定义自定义异常类
class AppError(Exception):
    """自定义应用级异常"""
    def __init__(self, error_type: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        self.message = message
        self.details = details
        super().__init__(self.message or self.error_type)

class ErrorHandler:
    """统一错误处理类"""
    
    def __init__(self):
        self.error_codes = {
            # ... (之前的错误码定义保持不变)
            'WALLET_NOT_CONNECTED': {'code': 1001, 'message': '钱包未连接', 'http_status': 401},
            'INVALID_INPUT': {'code': 1101, 'message': '无效的输入', 'http_status': 400},
            'ASSET_NOT_FOUND': {'code': 1202, 'message': '资产不存在', 'http_status': 404},
            'ASSET_NOT_AVAILABLE': {'code': 1205, 'message': '资产不可用', 'http_status': 400},
            'INSUFFICIENT_SUPPLY': {'code': 1206, 'message': '可售数量不足', 'http_status': 400},
            'DATABASE_ERROR': {'code': 1501, 'message': '数据库操作失败', 'http_status': 500},
            'INTERNAL_ERROR': {'code': 1502, 'message': '服务器内部错误', 'http_status': 500},
            'TRADE_NOT_FOUND': {'code': 1203, 'message': '交易记录不存在','http_status': 404},
            'TRADE_NOT_PENDING': {'code': 1207, 'message': '交易状态不正确','http_status': 400},
            'BLOCKCHAIN_TX_FAILED': {'code': 1402, 'message': '区块链交易失败','http_status': 500},
            'TRANSACTION_BUILD_FAILED': {'code': 1405, 'message': '构建交易失败','http_status': 500},
            'SOLANA_CONNECTION_FAILED': {'code': 1406, 'message': '无法连接到Solana节点','http_status': 503},
        }
    
    def format_error_response(self, 
                            error_type: str, 
                            message: Optional[str] = None,
                            details: Optional[Dict[str, Any]] = None,
                            field: Optional[str] = None) -> tuple[Dict[str, Any], int]:
        """
        格式化错误响应
        """
        error_info = self.error_codes.get(error_type, {
            'code': 9999,
            'message': '未知错误',
            'http_status': 500
        })
        
        final_message = message or error_info['message']
        
        error_response = {
            'success': False,
            'error': {
                'code': error_info['code'],
                'type': error_type,
                'message': final_message,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        if field:
            error_response['error']['field'] = field
        
        if details:
            error_response['error']['details'] = details
        
        return error_response, error_info['http_status']

    def create_json_response(self, 
                           error_type: str, 
                           message: Optional[str] = None,
                           details: Optional[Dict[str, Any]] = None,
                           field: Optional[str] = None):
        """
        创建JSON错误响应
        """
        error_response, status_code = self.format_error_response(
            error_type, message, details, field
        )
        return jsonify(error_response), status_code

# 全局错误处理器实例
global_error_handler = ErrorHandler()

# 全局错误处理函数
def error_handler(e: Exception):
    """全局异常处理器，捕获AppError和其他异常"""
    if isinstance(e, AppError):
        # 处理自定义的AppError
        logger.warning(f"捕获到应用错误 (AppError): {e.error_type} - {e.message}")
        return global_error_handler.create_json_response(
            error_type=e.error_type,
            message=e.message,
            details=e.details
        )
    else:
        # 处理未预料到的其他异常
        logger.error(f"捕获到未处理的异常: {e}", exc_info=True)
        return global_error_handler.create_json_response(
            error_type='INTERNAL_ERROR',
            message='服务器发生意外错误，请联系技术支持。'
        )

def create_error_response(error_type: str, 
                        message: Optional[str] = None,
                        details: Optional[Dict[str, Any]] = None,
                        field: Optional[str] = None):
    """
    便捷函数：创建错误响应
    """
    return global_error_handler.create_json_response(error_type, message, details, field)
