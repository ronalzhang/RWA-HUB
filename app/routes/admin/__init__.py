"""
管理后台模块化重构
- 将原来4200+行的admin.py拆分为多个专业模块
- 统一认证装饰器和权限管理
- 优化代码结构和可维护性
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session
from datetime import datetime

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
        from app.models.admin import SystemConfig
        
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
            # 直接验证私钥格式，不依赖环境变量
            import base58
            import base64
            from app.utils.solana_compat.keypair import Keypair
            
            # 检测私钥格式并转换
            try:
                if len(private_key) == 128:  # 十六进制格式
                    private_key_bytes = bytes.fromhex(private_key)
                elif len(private_key) == 88:  # Base64格式
                    private_key_bytes = base64.b64decode(private_key)
                else:  # Base58格式
                    private_key_bytes = base58.b58decode(private_key)
                
                # 如果是64字节，取前32字节作为seed
                if len(private_key_bytes) == 64:
                    seed = private_key_bytes[:32]
                elif len(private_key_bytes) == 32:
                    seed = private_key_bytes
                else:
                    return jsonify({'success': False, 'error': f'无效的私钥长度: {len(private_key_bytes)}字节，期望32或64字节'}), 400
                
                # 创建密钥对验证
                keypair = Keypair.from_seed(seed)
                wallet_address = str(keypair.public_key)
                
            except Exception as e:
                return jsonify({'success': False, 'error': f'私钥格式错误: {str(e)}'}), 400
            
            # 加密私钥
            crypto_manager = get_crypto_manager()
            encrypted_key = crypto_manager.encrypt_private_key(private_key)
            
            # 保存加密后的私钥到系统配置
            SystemConfig.set_value('SOLANA_PRIVATE_KEY_ENCRYPTED', encrypted_key, '管理员通过界面设置')
            
            # 保存加密密码到系统配置（注意：这里需要进一步加密）
            # 为了安全，我们使用一个固定的系统密钥来加密用户的加密密码
            system_crypto = get_crypto_manager()
            # 临时设置系统密钥
            os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
            encrypted_password = system_crypto.encrypt_private_key(crypto_password)
            SystemConfig.set_value('CRYPTO_PASSWORD_ENCRYPTED', encrypted_password, '系统加密的用户密码')
            
            # 设置环境变量以便立即生效
            os.environ['SOLANA_PRIVATE_KEY_ENCRYPTED'] = encrypted_key
            os.environ['CRYPTO_PASSWORD'] = crypto_password
            
            current_app.logger.info(f"私钥已加密并保存，钱包地址: {wallet_address}")
            
            return jsonify({
                'success': True,
                'encrypted_key': encrypted_key,
                'wallet_address': wallet_address,
                'message': '私钥已加密并保存到系统配置'
            })
            
        finally:
            # 恢复原始密码
            if original_password:
                os.environ['CRYPTO_PASSWORD'] = original_password
            elif 'CRYPTO_PASSWORD' in os.environ and crypto_password != os.environ.get('CRYPTO_PASSWORD'):
                # 如果不是刚设置的密码，则删除
                pass
        
    except Exception as e:
        current_app.logger.error(f"加密私钥失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/v2/api/crypto/load-encrypted-key', methods=['POST'])
@api_admin_required
def load_encrypted_key():
    """从系统配置加载加密私钥"""
    try:
        from app.models.admin import SystemConfig
        from app.utils.crypto_manager import get_crypto_manager
        
        # 获取加密的私钥和密码
        encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
        encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
        
        if not encrypted_key or not encrypted_password:
            return jsonify({
                'success': False,
                'error': '未找到加密的私钥配置，请先设置并加密私钥'
            })
        
        # 解密用户密码
        import os
        original_password = os.environ.get('CRYPTO_PASSWORD')
        os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
        
        try:
            system_crypto = get_crypto_manager()
            crypto_password = system_crypto.decrypt_private_key(encrypted_password)
            
            # 设置解密密码
            os.environ['CRYPTO_PASSWORD'] = crypto_password
            
            # 验证私钥
            user_crypto = get_crypto_manager()
            private_key = user_crypto.decrypt_private_key(encrypted_key)
            
            # 验证私钥格式
            from app.utils.helpers import get_solana_keypair_from_env
            os.environ['TEMP_PRIVATE_KEY'] = private_key
            result = get_solana_keypair_from_env('TEMP_PRIVATE_KEY')
            del os.environ['TEMP_PRIVATE_KEY']
            
            if not result:
                return jsonify({'success': False, 'error': '解密后的私钥无效'})
            
            # 设置环境变量
            os.environ['SOLANA_PRIVATE_KEY_ENCRYPTED'] = encrypted_key
            
            current_app.logger.info(f"成功加载加密私钥，钱包地址: {result['public_key']}")
            
            return jsonify({
                'success': True,
                'wallet_address': result['public_key'],
                'message': '加密私钥已成功加载'
            })
            
        finally:
            if original_password:
                os.environ['CRYPTO_PASSWORD'] = original_password
        
    except Exception as e:
        current_app.logger.error(f"加载加密私钥失败: {str(e)}")
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

@admin_bp.route('/test-encrypt')
def test_encrypt():
    """加密测试页面"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Encryption Test</title>
    </head>
    <body>
        <h1>Private Key Encryption Test</h1>
        <div>
            <label>Encryption Password:</label><br>
            <input type="password" id="password" value="test123456"><br><br>
            
            <label>Private Key (128 hex chars):</label><br>
            <textarea id="privateKey" rows="3" cols="80">0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef</textarea><br><br>
            
            <button onclick="encryptKey()">Encrypt Private Key</button><br><br>
            
            <div id="result"></div>
        </div>
        
        <script>
        async function encryptKey() {
            const password = document.getElementById('password').value;
            const privateKey = document.getElementById('privateKey').value;
            
            if (!password || !privateKey) {
                alert('Please enter both password and private key');
                return;
            }
            
            try {
                const response = await fetch('/admin/v2/api/crypto/encrypt-key', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        private_key: privateKey,
                        crypto_password: password
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    document.getElementById('result').innerHTML = 
                        '<h3>Success!</h3>' +
                        '<p><strong>Wallet Address:</strong> ' + result.wallet_address + '</p>' +
                        '<p><strong>Encrypted Key:</strong></p>' +
                        '<textarea rows="5" cols="80" readonly>' + result.encrypted_key + '</textarea>';
                } else {
                    document.getElementById('result').innerHTML = 
                        '<h3 style="color: red;">Error:</h3>' +
                        '<p>' + result.error + '</p>';
                }
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    '<h3 style="color: red;">Error:</h3>' +
                    '<p>' + error.message + '</p>';
            }
        }
        </script>
    </body>
    </html>
    '''

@admin_bp.route('/test-simple')
def test_simple():
    """简单的测试页面"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Test</title>
    </head>
    <body>
        <h1>API Test Page</h1>
        <button onclick="testAPI()">Test API</button>
        <div id="result"></div>
        
        <script>
        async function testAPI() {
            try {
                const response = await fetch('/admin/v2/api/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({test: 'data'})
                });
                
                const result = await response.json();
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
            } catch (error) {
                document.getElementById('result').innerHTML = 'Error: ' + error.message;
            }
        }
        </script>
    </body>
    </html>
    '''

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

# 添加钱包相关API
@admin_bp.route('/api/wallet-info', methods=['GET'])
@api_admin_required
def get_wallet_info():
    """获取钱包信息API"""
    try:
        from app.utils.helpers import get_solana_keypair_from_env
        
        # 获取钱包信息
        keypair_info = get_solana_keypair_from_env()
        
        if not keypair_info:
            return jsonify({
                'address': None,
                'balance': 0,
                'status': 'not_configured'
            })
        
        # TODO: 这里可以添加余额查询逻辑
        # 暂时返回模拟数据
        return jsonify({
            'address': keypair_info['public_key'],
            'balance': '0.0',  # 实际应该查询Solana网络
            'status': 'configured'
        })
        
    except Exception as e:
        current_app.logger.error(f"获取钱包信息失败: {str(e)}")
        return jsonify({
            'address': None,
            'balance': 0,
            'status': 'error',
            'error': str(e)
        })

@admin_bp.route('/api/test-wallet', methods=['POST'])
@api_admin_required  
def test_wallet_connection():
    """测试钱包连接API"""
    try:
        from app.utils.helpers import get_solana_keypair_from_env
        
        # 测试钱包连接
        keypair_info = get_solana_keypair_from_env()
        
        if not keypair_info:
            return jsonify({
                'success': False,
                'error': '未配置钱包或私钥无效'
            })
        
        # 如果能成功获取密钥对，说明连接正常
        return jsonify({
            'success': True,
            'message': '钱包连接测试成功',
            'address': keypair_info['public_key']
        })
        
    except Exception as e:
        current_app.logger.error(f"钱包连接测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'钱包连接测试失败: {str(e)}'
        })

# 注意：dashboard、assets、users、trades等路由已在各自模块中定义
# 避免重复定义导致路由冲突

# 添加管理员用户管理API
@admin_bp.route('/api/admins', methods=['GET'])
@api_admin_required
def get_admin_users():
    """获取管理员用户列表"""
    try:
        # 先测试基础功能
        current_app.logger.info("开始获取管理员列表")
        
        # 检查数据库连接
        from app.extensions import db
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        current_app.logger.info("数据库连接正常")
        
        # 检查AdminUser模型
        from app.models.admin import AdminUser
        current_app.logger.info("AdminUser模型导入成功")
        
        # 检查表是否存在
        try:
            admin_count = AdminUser.query.count()
            current_app.logger.info(f"AdminUser表存在，当前有{admin_count}条记录")
        except Exception as table_error:
            current_app.logger.error(f"AdminUser表访问失败: {str(table_error)}")
            return jsonify({'error': f'数据库表访问失败: {str(table_error)}'}), 500
        
        admins = AdminUser.query.all()
        admin_list = []
        
        for admin in admins:
            admin_list.append({
                'id': admin.id,
                'wallet_address': admin.wallet_address,
                'username': admin.username,
                'role': admin.role,
                'created_at': admin.created_at.isoformat() if admin.created_at else None,
                'last_login': admin.last_login.isoformat() if admin.last_login else None
            })
        
        current_app.logger.info(f"成功获取{len(admin_list)}个管理员")
        return jsonify(admin_list)
        
    except Exception as e:
        current_app.logger.error(f"获取管理员列表失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin_addresses', methods=['POST'])
@api_admin_required
def add_admin_user():
    """添加管理员用户"""
    try:
        current_app.logger.info("开始添加管理员用户")
        
        # 检查请求数据
        data = request.get_json()
        current_app.logger.info(f"接收到数据: {data}")
        
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        wallet_address = data.get('wallet_address')
        role = data.get('role', 'admin')
        description = data.get('description', '')
        
        current_app.logger.info(f"解析数据 - 地址: {wallet_address}, 角色: {role}, 描述: {description}")
        
        if not wallet_address:
            return jsonify({'error': '钱包地址不能为空'}), 400
        
        # 检查数据库连接
        from app.extensions import db
        from app.models.admin import AdminUser
        
        current_app.logger.info("开始检查地址是否已存在")
        
        # 检查地址是否已存在
        existing_admin = AdminUser.query.filter_by(wallet_address=wallet_address).first()
        if existing_admin:
            current_app.logger.warning(f"地址已存在: {wallet_address}")
            return jsonify({'error': '该钱包地址已是管理员'}), 400
        
        current_app.logger.info("开始创建新管理员")
        
        # 创建新管理员
        new_admin = AdminUser(
            wallet_address=wallet_address,
            role=role,
            username=description or f'管理员_{wallet_address[:8]}'
        )
        
        current_app.logger.info("开始保存到数据库")
        
        db.session.add(new_admin)
        db.session.commit()
        
        current_app.logger.info(f"新增管理员成功: {wallet_address}, 角色: {role}")
        
        return jsonify({
            'success': True,
            'message': '管理员添加成功',
            'admin': {
                'id': new_admin.id,
                'wallet_address': new_admin.wallet_address,
                'role': new_admin.role,
                'created_at': new_admin.created_at.isoformat()
            }
        })
        
    except Exception as e:
        try:
            from app.extensions import db
            db.session.rollback()
        except:
            pass
        current_app.logger.error(f"添加管理员失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin_addresses/<wallet_address>', methods=['PUT'])
@api_admin_required
def update_admin_user(wallet_address):
    """更新管理员用户"""
    try:
        from app.models.admin import AdminUser
        from app.extensions import db
        
        admin = AdminUser.query.filter_by(wallet_address=wallet_address).first()
        if not admin:
            return jsonify({'error': '管理员不存在'}), 404
        
        data = request.get_json()
        
        if 'role' in data:
            admin.role = data['role']
        
        if 'description' in data:
            admin.username = data['description']
        
        admin.updated_at = datetime.utcnow()
        db.session.commit()
        
        current_app.logger.info(f"更新管理员: {wallet_address}")
        
        return jsonify({
            'success': True,
            'message': '管理员更新成功'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新管理员失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin_addresses/<wallet_address>', methods=['DELETE'])
@api_admin_required
def delete_admin_user(wallet_address):
    """删除管理员用户"""
    try:
        from app.models.admin import AdminUser
        from app.extensions import db
        
        admin = AdminUser.query.filter_by(wallet_address=wallet_address).first()
        if not admin:
            return jsonify({'error': '管理员不存在'}), 404
        
        # 防止删除最后一个超级管理员
        if admin.role == 'super_admin':
            super_admin_count = AdminUser.query.filter_by(role='super_admin').count()
            if super_admin_count <= 1:
                return jsonify({'error': '不能删除最后一个超级管理员'}), 400
        
        db.session.delete(admin)
        db.session.commit()
        
        current_app.logger.info(f"删除管理员: {wallet_address}")
        
        return jsonify({
            'success': True,
            'message': '管理员删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除管理员失败: {str(e)}")
        return jsonify({'error': str(e)}), 500 