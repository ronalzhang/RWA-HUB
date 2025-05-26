"""
管理后台模块化重构
- 将原来4200+行的admin.py拆分为多个专业模块
- 统一认证装饰器和权限管理
- 优化代码结构和可维护性
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

# 导入所有子模块，确保路由被注册
from . import auth
from . import assets  
from . import users
from . import dashboard
from . import commission
from . import trades
from . import utils

# 导出常用函数，保持向后兼容
from .auth import admin_required, api_admin_required, admin_page_required, permission_required
from .utils import has_permission, get_admin_role, get_admin_info, is_valid_solana_address
from app.utils.decorators import is_admin

# 添加V2版本的页面路由（这些路由在各个专门模块中没有定义）
@admin_bp.route('/v2')
@admin_page_required
def admin_v2_index():
    """V2版本管理后台首页"""
    return render_template('admin_v2/dashboard.html')

@admin_bp.route('/v2/dashboard')
@admin_page_required
def dashboard_v2():
    """V2版本仪表盘页面"""
    return render_template('admin_v2/dashboard.html')

@admin_bp.route('/v2/assets')
@admin_page_required
def assets_v2():
    """V2版本资产管理页面"""
    return render_template('admin_v2/assets.html')

@admin_bp.route('/v2/users')
@admin_page_required
def users_v2():
    """V2版本用户管理页面"""
    return render_template('admin_v2/users.html')

@admin_bp.route('/v2/trades')
@admin_page_required
def trades_v2():
    """V2版本交易管理页面"""
    return render_template('admin_v2/trades.html')

@admin_bp.route('/v2/commission')
@admin_page_required
def commission_v2():
    """V2版本佣金管理页面"""
    return render_template('admin_v2/commission.html')

@admin_bp.route('/v2/settings')
@admin_page_required
def settings_v2():
    """V2版本系统设置页面"""
    from app.models.admin import SystemConfig
    
    # 获取所有配置
    configs = {}
    config_keys = [
        'PLATFORM_FEE_BASIS_POINTS',
        'PLATFORM_FEE_ADDRESS', 
        'PURCHASE_CONTRACT_ADDRESS',
        'ASSET_CREATION_FEE_AMOUNT',
        'ASSET_CREATION_FEE_ADDRESS'
    ]
    
    for key in config_keys:
        configs[key] = SystemConfig.get_value(key, '')
    
    return render_template('admin_v2/settings.html', configs=configs)

@admin_bp.route('/v2/settings', methods=['POST'])
@admin_page_required
def update_settings_v2():
    """更新系统设置"""
    from app.models.admin import SystemConfig
    from flask import request, flash, redirect, url_for, g
    
    try:
        # 获取管理员地址
        admin_address = getattr(g, 'eth_address', None) or session.get('admin_wallet_address')
        
        # 更新配置
        config_updates = {
            'PLATFORM_FEE_BASIS_POINTS': request.form.get('platform_fee_basis_points'),
            'PLATFORM_FEE_ADDRESS': request.form.get('platform_fee_address'),
            'PURCHASE_CONTRACT_ADDRESS': request.form.get('purchase_contract_address'),
            'ASSET_CREATION_FEE_AMOUNT': request.form.get('asset_creation_fee_amount'),
            'ASSET_CREATION_FEE_ADDRESS': request.form.get('asset_creation_fee_address')
        }
        
        for key, value in config_updates.items():
            if value is not None:
                SystemConfig.set_value(key, value, f'Updated by admin {admin_address}')
        
        flash('系统设置已成功更新', 'success')
        
    except Exception as e:
        flash(f'更新设置失败: {str(e)}', 'error')
        current_app.logger.error(f"更新系统设置失败: {str(e)}")
    
    return redirect(url_for('admin.settings_v2'))

@admin_bp.route('/v2/api/crypto/encrypt-key', methods=['POST'])
@api_admin_required
def encrypt_private_key():
    """加密私钥API"""
    try:
        from app.utils.crypto_manager import get_crypto_manager
        
        data = request.get_json()
        private_key = data.get('private_key')
        crypto_password = data.get('crypto_password')
        
        if not private_key:
            return jsonify({'success': False, 'error': '私钥不能为空'}), 400
        
        if not crypto_password:
            return jsonify({'success': False, 'error': '加密密码不能为空'}), 400
        
        # 临时设置加密密码
        import os
        original_password = os.environ.get('CRYPTO_PASSWORD')
        os.environ['CRYPTO_PASSWORD'] = crypto_password
        
        try:
            # 验证私钥格式
            from app.utils.helpers import get_solana_keypair_from_env
            
            # 临时设置环境变量进行验证
            os.environ['TEMP_PRIVATE_KEY'] = private_key
            result = get_solana_keypair_from_env('TEMP_PRIVATE_KEY')
            del os.environ['TEMP_PRIVATE_KEY']
            
            if not result:
                return jsonify({'success': False, 'error': '无效的私钥格式'}), 400
            
            # 加密私钥
            crypto_manager = get_crypto_manager()
            encrypted_key = crypto_manager.encrypt_private_key(private_key)
            
            return jsonify({
                'success': True,
                'encrypted_key': encrypted_key,
                'wallet_address': result['public_key']
            })
            
        finally:
            # 恢复原始密码
            if original_password:
                os.environ['CRYPTO_PASSWORD'] = original_password
            elif 'CRYPTO_PASSWORD' in os.environ:
                del os.environ['CRYPTO_PASSWORD']
        
    except Exception as e:
        current_app.logger.error(f"加密私钥失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/v2/api/crypto/test-key', methods=['POST'])
@api_admin_required
def test_encrypted_key():
    """测试加密私钥API"""
    try:
        from app.utils.crypto_manager import get_crypto_manager
        
        data = request.get_json()
        encrypted_key = data.get('encrypted_key')
        
        if not encrypted_key:
            return jsonify({'success': False, 'error': '加密私钥不能为空'}), 400
        
        # 解密并验证
        crypto_manager = get_crypto_manager()
        decrypted_key = crypto_manager.decrypt_private_key(encrypted_key)
        
        # 验证解密后的私钥
        from app.utils.helpers import get_solana_keypair_from_env
        import os
        
        os.environ['TEMP_PRIVATE_KEY'] = decrypted_key
        result = get_solana_keypair_from_env('TEMP_PRIVATE_KEY')
        del os.environ['TEMP_PRIVATE_KEY']
        
        if not result:
            return jsonify({'success': False, 'error': '解密后的私钥无效'}), 400
        
        return jsonify({
            'success': True,
            'wallet_address': result['public_key'],
            'message': '私钥解密和验证成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"测试加密私钥失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/v2/admin-users')
@admin_page_required
def admin_users_v2():
    """V2版本管理员用户页面"""
    return render_template('admin_v2/admin_users.html')

@admin_bp.route('/test')
def test_route():
    """测试路由，不需要认证"""
    return "Admin routes are working!"

@admin_bp.route('/test-settings')
def test_settings():
    """测试设置页面，不需要认证"""
    from app.models.admin import SystemConfig
    
    # 获取所有配置
    configs = {}
    config_keys = [
        'PLATFORM_FEE_BASIS_POINTS',
        'PLATFORM_FEE_ADDRESS', 
        'PURCHASE_CONTRACT_ADDRESS',
        'ASSET_CREATION_FEE_AMOUNT',
        'ASSET_CREATION_FEE_ADDRESS'
    ]
    
    for key in config_keys:
        configs[key] = SystemConfig.get_value(key, '')
    
    return render_template('admin_v2/settings.html', configs=configs)

@admin_bp.route('/api/set-temp-env', methods=['POST'])
@api_admin_required
def set_temp_env():
    """设置临时环境变量"""
    try:
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')
        
        if not key or not value:
            return jsonify({'success': False, 'error': '缺少key或value'}), 400
        
        # 设置临时环境变量
        import os
        os.environ[key] = value
        
        return jsonify({'success': True, 'message': f'环境变量{key}已设置'})
        
    except Exception as e:
        current_app.logger.error(f"设置临时环境变量失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/v2/api/test', methods=['GET', 'POST'])
def test_api():
    """测试API，不需要认证"""
    return jsonify({
        'success': True,
        'message': 'API工作正常',
        'method': request.method,
        'data': request.get_json() if request.method == 'POST' else None
    })

# 注意：dashboard、assets、users、trades等路由已在各自模块中定义
# 避免重复定义导致路由冲突 