#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
认证工具模块
提供管理员认证等功能
"""

from functools import wraps
from flask import request, jsonify, session, redirect, url_for, current_app
import hashlib

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简化的管理员认证逻辑
        # 检查session中是否有管理员标识
        if not session.get('is_admin'):
            # 检查是否有管理员密码参数
            admin_password = request.args.get('admin_password') or request.form.get('admin_password')
            if admin_password:
                # 简单的密码验证（实际应用中应该使用更安全的方式）
                expected_password = current_app.config.get('ADMIN_PASSWORD', 'admin123')
                if admin_password == expected_password:
                    session['is_admin'] = True
                    current_app.logger.info("管理员认证成功")
                else:
                    current_app.logger.warning("管理员密码错误")
                    return jsonify({'error': '管理员密码错误'}), 401
            else:
                return jsonify({'error': '需要管理员权限'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def eth_address_required(f):
    """以太坊地址验证装饰器（简化版）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 这里可以添加以太坊地址验证逻辑
        # 暂时跳过验证
        return f(*args, **kwargs)
    return decorated_function