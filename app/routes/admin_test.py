from flask import Blueprint, jsonify, current_app, g, request
from app.utils.decorators import eth_address_required
from app.utils.admin import get_admin_permissions, is_admin, has_permission

admin_test_bp = Blueprint('admin_test', __name__, url_prefix='/api/admin/test')

@admin_test_bp.route('/config')
@eth_address_required
def get_admin_config():
    """测试获取管理员配置"""
    try:
        # 获取管理员配置
        admin_config = current_app.config.get('ADMIN_CONFIG', {})
        
        # 获取当前连接的钱包地址
        current_address = g.eth_address
        
        # 检查是否是管理员
        admin_info = get_admin_permissions(current_address)
        is_admin_user = is_admin(current_address)
        
        # 返回详细配置信息（删除敏感信息）
        safe_config = {}
        for address, info in admin_config.items():
            safe_config[address] = {
                'role': info.get('role', 'admin'),
                'level': info.get('level', 1),
                'name': info.get('name', '管理员')
            }
            
        return jsonify({
            'success': True,
            'current_address': current_address,
            'is_admin': is_admin_user,
            'admin_info': admin_info,
            'config': safe_config
        })
    except Exception as e:
        current_app.logger.error(f"获取管理员配置失败: {str(e)}")
        return jsonify({'error': '获取管理员配置失败', 'message': str(e)}), 500
        
@admin_test_bp.route('/permission')
@eth_address_required
def check_permission():
    """测试检查特定权限"""
    try:
        # 获取要检查的权限
        permission = request.args.get('permission', '')
        
        # 获取当前连接的钱包地址
        current_address = g.eth_address
        
        # 检查是否有该权限
        has_perm = has_permission(permission, current_address)
        
        return jsonify({
            'success': True,
            'current_address': current_address,
            'permission': permission,
            'has_permission': has_perm
        })
    except Exception as e:
        current_app.logger.error(f"检查权限失败: {str(e)}")
        return jsonify({'error': '检查权限失败', 'message': str(e)}), 500 