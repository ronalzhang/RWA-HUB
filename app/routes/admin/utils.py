"""
管理后台通用工具函数
"""

import base58
from flask import current_app, session, request, g
from functools import wraps
from app.models.admin import AdminUser
from app.utils.admin import get_admin_permissions
from sqlalchemy import func


def is_valid_solana_address(address):
    """验证Solana地址格式"""
    if not address or not (32 <= len(address) <= 44):
        return False
    try:
        base58.b58decode(address)
        return True
    except ValueError:
        return False


def get_admin_info(eth_address):
    """获取管理员权限信息"""
    if not eth_address:
        return None
        
    # 区分ETH和SOL地址处理
    if eth_address.startswith('0x'):
        normalized_address = eth_address.lower()
    else:
        normalized_address = eth_address
    
    admin_config = current_app.config.get('ADMIN_CONFIG', {})
    admin_info = None
    
    # 检查地址是否在管理员配置中
    for admin_address, info in admin_config.items():
        if admin_address.startswith('0x'):
            config_address = admin_address.lower()
        else:
            config_address = admin_address
            
        if normalized_address == config_address:
            admin_info = info
            break
    
    if admin_info:
        return {
            'is_admin': True,
            'role': admin_info['role'],
            'name': admin_info['name'],
            'level': admin_info['level'],
            'permissions': admin_info['permissions']
        }
    
    return None


def has_permission(permission, eth_address=None):
    """检查管理员是否有特定权限"""
    target_address = eth_address if eth_address else getattr(g, 'eth_address', None)
    admin_info = get_admin_info(target_address)
    
    if not admin_info:
        return False
        
    # 检查权限等级
    permission_levels = current_app.config.get('PERMISSION_LEVELS', {})
    required_level = permission_levels.get(permission, 1)
    if admin_info['level'] <= required_level:
        return True
        
    # 检查具体权限列表
    return permission in admin_info['permissions']


def get_admin_role(eth_address=None):
    """获取管理员角色信息"""
    admin_info = get_admin_info(eth_address)
    return admin_info.get('role') if admin_info else None 