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
from . import monitoring
from . import news_hotspot  # 添加新闻热点模块
from . import ip_security   # 添加IP安全管理模块

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

@admin_bp.route('/v2/share-messages')
@admin_page_required
def share_messages_v2():
    """V2版本分享消息管理页面"""
    return render_template('admin_v2/share_messages.html')

@admin_bp.route('/share-messages')
@admin_page_required
def share_messages():
    """分享消息管理页面"""
    return render_template('admin_v2/share_messages.html')

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
                # 优先尝试base58解码（Solana最常用格式）
                try:
                    private_key_bytes = base58.b58decode(private_key)
                except:
                    # 如果base58失败，尝试其他格式
                    if len(private_key) == 128:  # 十六进制格式
                        private_key_bytes = bytes.fromhex(private_key)
                    elif len(private_key) == 88:  # Base64格式
                        private_key_bytes = base64.b64decode(private_key)
                    else:
                        raise ValueError(f"无法识别的私钥格式，长度: {len(private_key)}")
                
                # 处理不同长度的私钥
                
                if len(private_key_bytes) == 64:
                    # 标准64字节格式，前32字节是私钥
                    seed = private_key_bytes[:32]
                elif len(private_key_bytes) == 32:
                    # 仅私钥
                    seed = private_key_bytes
                elif len(private_key_bytes) == 66:
                    # 可能包含校验和，取前32字节作为私钥
                    seed = private_key_bytes[:32]
                else:
                    return jsonify({'success': False, 'error': f'无效的私钥长度: {len(private_key_bytes)}字节，期望32、64或66字节'}), 400
                
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
        from app.utils.solana_compat.keypair import Keypair
        import base58
        import base64
        
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
            
            # 解析私钥并生成地址
            # 优先尝试base58解码（Solana最常用格式）
            try:
                private_key_bytes = base58.b58decode(private_key)
            except:
                # 如果base58失败，尝试其他格式
                if len(private_key) == 128:  # 十六进制格式
                    private_key_bytes = bytes.fromhex(private_key)
                elif len(private_key) == 88:  # Base64格式
                    private_key_bytes = base64.b64decode(private_key)
                else:
                    raise ValueError(f"无法识别的私钥格式，长度: {len(private_key)}")
            
            # 处理不同长度的私钥
            if len(private_key_bytes) == 64:
                # 标准64字节格式，前32字节是私钥
                seed = private_key_bytes[:32]
            elif len(private_key_bytes) == 32:
                # 仅私钥
                seed = private_key_bytes
            elif len(private_key_bytes) == 66:
                # 可能包含校验和，取前32字节作为私钥
                seed = private_key_bytes[:32]
            else:
                raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}字节")
            
            # 创建密钥对验证
            keypair = Keypair.from_seed(seed)
            wallet_address = str(keypair.public_key)
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'私钥格式错误: {str(e)}'}), 400
        
        current_app.logger.info(f"成功加载加密私钥，钱包地址: {wallet_address}")
        
        return jsonify({
            'success': True,
            'wallet_address': wallet_address,
            'private_key': private_key,  # 返回解密后的私钥供前端填充表单
            'crypto_password': crypto_password,  # 返回解密后的密码供前端填充表单
            'message': '加密私钥已成功加载'
        })
        
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

# 上链历史记录相关API
@admin_bp.route('/v2/api/onchain-history', methods=['GET'])
@api_admin_required
def get_onchain_history():
    """获取上链历史记录"""
    try:
        from app.models.admin import OnchainHistory
        from sqlalchemy import desc
        
        # 获取查询参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        status = request.args.get('status', '')
        trigger_type = request.args.get('trigger_type', '')
        onchain_type = request.args.get('onchain_type', '')
        
        # 构建查询
        query = OnchainHistory.query
        
        if status:
            query = query.filter(OnchainHistory.status == status)
        if trigger_type:
            query = query.filter(OnchainHistory.trigger_type == trigger_type)
        if onchain_type:
            query = query.filter(OnchainHistory.onchain_type == onchain_type)
        
        # 按创建时间倒序排列
        query = query.order_by(desc(OnchainHistory.created_at))
        
        # 分页
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        records = [record.to_dict() for record in pagination.items]
        
        return jsonify({
            'success': True,
            'data': records,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取上链历史记录失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/v2/api/onchain-history/<int:record_id>/retry', methods=['POST'])
@api_admin_required
def retry_onchain_record(record_id):
    """重试上链操作"""
    try:
        from app.models.admin import OnchainHistory
        from app.extensions import db
        
        record = OnchainHistory.query.get_or_404(record_id)
        
        if not record.can_retry():
            return jsonify({
                'success': False, 
                'error': '该记录不能重试（已达到最大重试次数或状态不允许）'
            }), 400
        
        # 重置状态为待处理，增加重试次数
        record.status = 'pending'
        record.retry_count += 1
        record.error_message = None
        record.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # 这里可以添加实际的重试逻辑，比如发送到队列等
        # TODO: 实际的上链重试逻辑
        
        current_app.logger.info(f"上链记录 {record_id} 已标记为重试")
        
        return jsonify({
            'success': True,
            'message': '重试请求已提交'
        })
        
    except Exception as e:
        current_app.logger.error(f"重试上链操作失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/v2/api/onchain-history/export', methods=['GET'])
@api_admin_required
def export_onchain_history():
    """导出上链历史记录"""
    try:
        from app.models.admin import OnchainHistory
        from flask import make_response
        import csv
        import io
        
        # 获取筛选参数
        status = request.args.get('status', '')
        trigger_type = request.args.get('trigger_type', '')
        onchain_type = request.args.get('onchain_type', '')
        
        # 构建查询
        query = OnchainHistory.query
        
        if status:
            query = query.filter(OnchainHistory.status == status)
        if trigger_type:
            query = query.filter(OnchainHistory.trigger_type == trigger_type)
        if onchain_type:
            query = query.filter(OnchainHistory.onchain_type == onchain_type)
        
        # 按创建时间倒序排列
        records = query.order_by(OnchainHistory.created_at.desc()).all()
        
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            'ID', '资产ID', '资产名称', '资产符号', '交易ID', '触发类型', 
            '上链类型', '状态', '交易哈希', '区块号', 'Gas消耗', 'Gas价格',
            '重试次数', '最大重试次数', '触发者', '触发时间', '处理完成时间',
            '错误信息', '创建时间', '更新时间'
        ])
        
        # 写入数据
        for record in records:
            # 状态文本映射
            status_text = {
                'pending': '待上链',
                'processing': '上链中',
                'success': '上链成功',
                'failed': '上链失败',
                'retry': '重试中'
            }.get(record.status, record.status)
            
            # 触发类型文本映射
            trigger_text = {
                'payment_confirmed': '支付确认',
                'manual_trigger': '手动触发'
            }.get(record.trigger_type, record.trigger_type)
            
            # 上链类型文本映射
            onchain_text = {
                'asset_creation': '资产创建',
                'asset_update': '资产更新',
                'trade_settlement': '交易结算'
            }.get(record.onchain_type, record.onchain_type)
            
            writer.writerow([
                record.id,
                record.asset_id,
                record.asset_name if hasattr(record, 'asset_name') else (record.asset.name if record.asset else 'N/A'),
                record.asset_symbol if hasattr(record, 'asset_symbol') else (record.asset.token_symbol if record.asset else 'N/A'),
                record.trade_id or '',
                trigger_text,
                onchain_text,
                status_text,
                record.transaction_hash or '',
                record.block_number or '',
                record.gas_used or '',
                record.gas_price or '',
                record.retry_count,
                record.max_retries,
                record.triggered_by or '',
                record.triggered_at.strftime('%Y-%m-%d %H:%M:%S') if record.triggered_at else '',
                record.processed_at.strftime('%Y-%m-%d %H:%M:%S') if record.processed_at else '',
                record.error_message or '',
                record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else '',
                record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if record.updated_at else ''
            ])
        
        # 创建响应
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=onchain_history_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"导出上链历史记录失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500









# 注意：dashboard、assets、users、trades等路由已在各自模块中定义
# 避免重复定义导致路由冲突

# 添加钱包相关API
@admin_bp.route('/api/wallet-info', methods=['GET'])
@api_admin_required
def get_wallet_info():
    """获取钱包信息API"""
    try:
        from app.models.admin import SystemConfig
        from app.utils.crypto_manager import get_crypto_manager
        from app.utils.solana_compat.keypair import Keypair
        import base58
        import base64
        
        # 尝试从数据库获取加密的私钥
        encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
        encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
        
        if not encrypted_key or not encrypted_password:
            return jsonify({
                'address': None,
                'balance': 0,
                'status': 'not_configured'
            })
        
        try:
            # 解密私钥
            import os
            original_password = os.environ.get('CRYPTO_PASSWORD')
            os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
            
            system_crypto = get_crypto_manager()
            crypto_password = system_crypto.decrypt_private_key(encrypted_password)
            
            os.environ['CRYPTO_PASSWORD'] = crypto_password
            user_crypto = get_crypto_manager()
            private_key = user_crypto.decrypt_private_key(encrypted_key)
            
            # 解析私钥并生成地址
            # 优先尝试base58解码（Solana最常用格式）
            try:
                private_key_bytes = base58.b58decode(private_key)
            except:
                # 如果base58失败，尝试其他格式
                if len(private_key) == 128:  # 十六进制格式
                    private_key_bytes = bytes.fromhex(private_key)
                elif len(private_key) == 88:  # Base64格式
                    private_key_bytes = base64.b64decode(private_key)
                else:
                    raise ValueError(f"无法识别的私钥格式，长度: {len(private_key)}")
            
            # 处理不同长度的私钥
            if len(private_key_bytes) == 64:
                seed = private_key_bytes[:32]
            elif len(private_key_bytes) == 32:
                seed = private_key_bytes
            elif len(private_key_bytes) == 66:
                seed = private_key_bytes[:32]
            else:
                raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}字节")
            
            keypair = Keypair.from_seed(seed)
            wallet_address = str(keypair.public_key)
            
            # 查询SOL余额
            try:
                import requests
                from solana.rpc.api import Client
                from solana.publickey import PublicKey
                
                # 使用主网RPC端点，设置较短的超时时间
                client = Client("https://api.mainnet-beta.solana.com", timeout=5)
                public_key = PublicKey(wallet_address)
                
                # 获取余额（以lamports为单位）
                balance_response = client.get_balance(public_key)
                if balance_response.value is not None:
                    # 转换为SOL（1 SOL = 1,000,000,000 lamports）
                    balance_sol = balance_response.value / 1_000_000_000
                    balance_str = f"{balance_sol:.9f}"
                else:
                    balance_str = "查询失败"
                    
            except Exception as balance_error:
                current_app.logger.warning(f"查询SOL余额失败: {balance_error}")
                # 简化错误处理，直接返回0.0
                balance_str = "0.0"
            
            # 恢复原始密码
            if original_password:
                os.environ['CRYPTO_PASSWORD'] = original_password
            
            return jsonify({
                'address': wallet_address,
                'balance': balance_str,
                'status': 'configured'
            })
            
        except Exception as decrypt_error:
            current_app.logger.error(f"解密私钥失败: {decrypt_error}")
            return jsonify({
                'address': None,
                'balance': 0,
                'status': 'error',
                'error': f'解密失败: {str(decrypt_error)}'
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
        from app.models.admin import SystemConfig
        from app.utils.crypto_manager import get_crypto_manager
        from app.utils.solana_compat.keypair import Keypair
        import base58
        import base64
        
        # 尝试从数据库获取加密的私钥
        encrypted_key = SystemConfig.get_value('SOLANA_PRIVATE_KEY_ENCRYPTED')
        encrypted_password = SystemConfig.get_value('CRYPTO_PASSWORD_ENCRYPTED')
        
        if not encrypted_key or not encrypted_password:
            return jsonify({
                'success': False,
                'error': '未配置钱包或私钥无效'
            })
        
        try:
            # 解密私钥
            import os
            original_password = os.environ.get('CRYPTO_PASSWORD')
            os.environ['CRYPTO_PASSWORD'] = 'RWA_HUB_SYSTEM_KEY_2024'
            
            system_crypto = get_crypto_manager()
            crypto_password = system_crypto.decrypt_private_key(encrypted_password)
            
            os.environ['CRYPTO_PASSWORD'] = crypto_password
            user_crypto = get_crypto_manager()
            private_key = user_crypto.decrypt_private_key(encrypted_key)
            
            # 解析私钥并生成地址
            # 优先尝试base58解码（Solana最常用格式）
            try:
                private_key_bytes = base58.b58decode(private_key)
            except:
                # 如果base58失败，尝试其他格式
                if len(private_key) == 128:  # 十六进制格式
                    private_key_bytes = bytes.fromhex(private_key)
                elif len(private_key) == 88:  # Base64格式
                    private_key_bytes = base64.b64decode(private_key)
                else:
                    raise ValueError(f"无法识别的私钥格式，长度: {len(private_key)}")
            
            # 处理不同长度的私钥
            if len(private_key_bytes) == 64:
                seed = private_key_bytes[:32]
            elif len(private_key_bytes) == 32:
                seed = private_key_bytes
            elif len(private_key_bytes) == 66:
                seed = private_key_bytes[:32]
            else:
                raise ValueError(f"无效的私钥长度: {len(private_key_bytes)}字节")
            
            keypair = Keypair.from_seed(seed)
            wallet_address = str(keypair.public_key)
            
            # 恢复原始密码
            if original_password:
                os.environ['CRYPTO_PASSWORD'] = original_password
            
            return jsonify({
                'success': True,
                'message': '钱包连接测试成功',
                'address': wallet_address
            })
            
        except Exception as decrypt_error:
            current_app.logger.error(f"解密私钥失败: {decrypt_error}")
            return jsonify({
                'success': False,
                'error': f'解密失败: {str(decrypt_error)}'
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