from flask import current_app

def get_admin_permissions(eth_address):
    """获取管理员权限"""
    try:
        if not eth_address:
            current_app.logger.warning('未提供钱包地址')
            return None
        
        current_app.logger.info(f'检查管理员权限 - 原始地址: {eth_address}')
        
        # 区分ETH和SOL地址处理
        # ETH地址以0x开头，需要转换为小写
        # SOL地址不以0x开头，保持原样（大小写敏感）
        if eth_address.startswith('0x'):
            normalized_address = eth_address.lower()
            current_app.logger.info(f'ETH地址，转换为小写: {normalized_address}')
        else:
            normalized_address = eth_address
            current_app.logger.info(f'非ETH地址（可能是SOL），保持原样: {normalized_address}')
        
        admin_config = current_app.config.get('ADMIN_CONFIG', {})
        if not admin_config:
            current_app.logger.error('ADMIN_CONFIG 未配置')
            return None
            
        current_app.logger.info(f'管理员配置: {admin_config}')
        admin_info = None
        
        # 检查地址是否在管理员配置中
        for admin_address, info in admin_config.items():
            # 同样区分ETH和SOL地址处理
            if admin_address.startswith('0x'):
                config_address = admin_address.lower()
            else:
                config_address = admin_address
                
            current_app.logger.debug(f'比较地址: {config_address} vs {normalized_address}')
            if normalized_address == config_address:
                admin_info = info
                current_app.logger.info(f'找到管理员信息: {info}')
                break
        
        if admin_info:
            result = {
                'is_admin': True,
                'role': admin_info.get('role', 'admin'),
                'name': admin_info.get('name', '管理员'),
                'level': admin_info.get('level', 1),
                'permissions': admin_info.get('permissions', [])
            }
            current_app.logger.info(f'返回管理员信息: {result}')
            return result
        
        current_app.logger.warning(f'地址 {eth_address} 不是管理员')
        return None
        
    except Exception as e:
        current_app.logger.error(f'检查管理员权限时出错: {str(e)}')
        return None

def is_admin(eth_address=None):
    """检查指定地址是否是管理员"""
    try:
        if not eth_address:
            current_app.logger.warning('未提供钱包地址')
            return False
            
        current_app.logger.info(f'检查是否是管理员 - 地址: {eth_address}')
        result = get_admin_permissions(eth_address) is not None
        current_app.logger.info(f'检查结果: {result}')
        return result
        
    except Exception as e:
        current_app.logger.error(f'检查管理员状态时出错: {str(e)}')
        return False

def has_permission(permission, eth_address=None):
    """检查管理员是否有特定权限"""
    try:
        if not eth_address:
            current_app.logger.warning('未提供钱包地址')
            return False
            
        current_app.logger.info(f'检查权限 {permission} - 地址: {eth_address}')
        admin_info = get_admin_permissions(eth_address)
        
        if not admin_info:
            current_app.logger.warning('不是管理员')
            return False
            
        # 检查权限等级
        required_level = current_app.config.get('PERMISSION_LEVELS', {}).get(permission, 1)
        current_app.logger.info(f'所需权限等级: {required_level}, 当前等级: {admin_info["level"]}')
        
        if admin_info['level'] <= required_level:  # 级别数字越小，权限越大
            current_app.logger.info('权限等级检查通过')
            return True
            
        # 如果没有通过等级检查，则检查具体权限列表
        result = permission in admin_info['permissions']
        current_app.logger.info(f'权限列表检查结果: {result}')
        return result
        
    except Exception as e:
        current_app.logger.error(f'检查权限时出错: {str(e)}')
        return False 