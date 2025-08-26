#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
认证工具模块
提供管理员认证等功能
"""

from functools import wraps
from flask import request, jsonify, session, redirect, url_for, current_app, g
import hashlib

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简化的管理员认证逻辑
        if not session.get('is_admin'):
            admin_password = request.args.get('admin_password') or request.form.get('admin_password')
            if admin_password:
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
        eth_address = request.headers.get('X-Eth-Address')
        
        if not eth_address:
            return jsonify({'error': '缺少以太坊地址'}), 400
        
        if len(eth_address) < 10:
            return jsonify({'error': '无效的以太坊地址格式'}), 400
        
        g.eth_address = eth_address
        
        return f(*args, **kwargs)
    return decorated_function

def wallet_address_required(f):
    """通用钱包地址验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        wallet_address = request.headers.get('X-Wallet-Address')
        
        if not wallet_address:
            # 兼容旧的 X-Eth-Address
            wallet_address = request.headers.get('X-Eth-Address')

        if not wallet_address:
            return jsonify({'success': False, 'error': '请求头中缺少 X-Wallet-Address'}), 401
        
        # 将地址传递给视图函数
        return f(wallet_address, *args, **kwargs)
    return decorated_function
