"""
API响应辅助函数
用于统一API响应格式
"""
from flask import jsonify


def success_response(data=None, message=None):
    """
    成功响应格式

    Args:
        data: 响应数据
        message: 成功消息

    Returns:
        Flask JSON响应
    """
    response = {
        'success': True
    }

    if data is not None:
        response['data'] = data

    if message:
        response['message'] = message

    return jsonify(response), 200


def error_response(error_code=None, message=None, status_code=400):
    """
    错误响应格式

    Args:
        error_code: 错误代码
        message: 错误消息
        status_code: HTTP状态码

    Returns:
        Flask JSON响应
    """
    response = {
        'success': False
    }

    if error_code:
        response['error'] = error_code

    if message:
        response['message'] = message

    return jsonify(response), status_code