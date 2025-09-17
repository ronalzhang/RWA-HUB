"""
系统配置管理API路由
用于管理加密密钥、平台私钥等敏感配置
"""

from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.admin import SystemConfig
from app.utils.crypto_manager import CryptoManager
from app.routes.admin_api import admin_required, permission_required, log_admin_operation
import base58
from solders.keypair import Keypair
import secrets
import logging

logger = logging.getLogger(__name__)

# 创建系统配置管理蓝图
system_config_bp = Blueprint('system_config', __name__, url_prefix='/admin/api/v2/system')

@system_config_bp.route('/config', methods=['GET'])
@admin_required
def get_system_config():
    """获取系统配置信息"""
    try:
        # 获取重要的系统配置状态
        configs = {
            'SYSTEM_MASTER_KEY_CONFIGURED': SystemConfig.get_value('SYSTEM_MASTER_KEY_CONFIGURED', 'false'),
            'PLATFORM_SPL_KEYPAIR_CONFIGURED': 'true' if current_app.config.get('PLATFORM_SPL_KEYPAIR') else 'false',
            'CRYPTO_PASSWORD_CONFIGURED': 'true' if current_app.config.get('CRYPTO_PASSWORD') else 'false'
        }

        # 检查平台钱包地址
        platform_wallet = current_app.config.get('PLATFORM_TREASURY_WALLET', 'NOT_SET')

        return jsonify({
            'success': True,
            'config': configs,
            'platform_wallet': platform_wallet,
            'message': '系统配置获取成功'
        })

    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取系统配置失败',
            'message': str(e)
        }), 500

@system_config_bp.route('/master-key', methods=['POST'])
@admin_required
@permission_required('管理系统')
@log_admin_operation('生成系统主密钥')
def generate_master_key():
    """生成新的系统主密钥"""
    try:
        # 生成64位随机密钥
        new_master_key = secrets.token_hex(32)

        # 使用临时加密密码来加密主密钥
        temp_crypto_password = 'SYSTEM_KEY_ENCRYPTION_PASSWORD_2024'

        # 创建临时加密管理器
        import os
        original_password = os.environ.get('CRYPTO_PASSWORD')
        os.environ['CRYPTO_PASSWORD'] = temp_crypto_password

        try:
            crypto_manager = CryptoManager()
            encrypted_master_key = crypto_manager.encrypt_private_key(new_master_key)

            # 保存到数据库
            SystemConfig.set_value('SYSTEM_MASTER_KEY_ENCRYPTED', encrypted_master_key)
            SystemConfig.set_value('SYSTEM_MASTER_KEY_CONFIGURED', 'true')

            logger.info("系统主密钥生成并保存成功")

            return jsonify({
                'success': True,
                'message': '系统主密钥生成成功',
                'master_key': new_master_key  # 仅在生成时返回，用于用户保存
            })

        finally:
            # 恢复原始密码
            if original_password:
                os.environ['CRYPTO_PASSWORD'] = original_password
            else:
                os.environ.pop('CRYPTO_PASSWORD', None)

    except Exception as e:
        logger.error(f"生成系统主密钥失败: {e}")
        return jsonify({
            'success': False,
            'error': '生成系统主密钥失败',
            'message': str(e)
        }), 500

@system_config_bp.route('/platform-keypair', methods=['POST'])
@admin_required
@permission_required('管理系统')
@log_admin_operation('设置平台私钥')
def set_platform_keypair():
    """设置平台SPL Token私钥"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请提供有效的JSON数据'
            }), 400

        private_key_input = data.get('private_key', '').strip()
        target_address = data.get('target_address', '').strip()

        if not private_key_input:
            return jsonify({
                'success': False,
                'error': '私钥不能为空'
            }), 400

        if not target_address:
            # 使用配置中的默认地址
            target_address = current_app.config.get('PLATFORM_TREASURY_WALLET')
            if not target_address:
                return jsonify({
                    'success': False,
                    'error': '未指定目标地址且配置中无默认地址'
                }), 400

        # 验证私钥格式
        try:
            private_key_bytes = base58.b58decode(private_key_input)
            keypair = Keypair.from_bytes(private_key_bytes)
            actual_address = str(keypair.pubkey())

            if actual_address != target_address:
                return jsonify({
                    'success': False,
                    'error': f'私钥对应地址 {actual_address} 与目标地址 {target_address} 不匹配'
                }), 400

        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'私钥格式无效: {str(e)}'
            }), 400

        # 加密并保存私钥
        try:
            crypto_manager = CryptoManager()
            private_key_hex = private_key_bytes.hex()
            encrypted_keypair = crypto_manager.encrypt_private_key(private_key_hex)

            # 保存到系统配置
            SystemConfig.set_value('PLATFORM_SPL_KEYPAIR', encrypted_keypair)
            SystemConfig.set_value('PLATFORM_SPL_KEYPAIR_ADDRESS', actual_address)

            logger.info(f"平台SPL Token私钥设置成功: {actual_address}")

            return jsonify({
                'success': True,
                'message': '平台SPL Token私钥设置成功',
                'address': actual_address
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'私钥加密失败: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"设置平台私钥失败: {e}")
        return jsonify({
            'success': False,
            'error': '设置平台私钥失败',
            'message': str(e)
        }), 500

@system_config_bp.route('/platform-keypair', methods=['GET'])
@admin_required
def get_platform_keypair_status():
    """获取平台私钥状态"""
    try:
        # 检查各种来源的私钥配置
        sources = {
            'database': SystemConfig.get_value('PLATFORM_SPL_KEYPAIR'),
            'config': current_app.config.get('PLATFORM_SPL_KEYPAIR'),
            'environment': current_app.config.get('PLATFORM_SPL_KEYPAIR')  # 这实际上来自环境变量
        }

        # 检查地址配置
        addresses = {
            'database': SystemConfig.get_value('PLATFORM_SPL_KEYPAIR_ADDRESS'),
            'config': current_app.config.get('PLATFORM_TREASURY_WALLET'),
        }

        # 尝试测试解密
        test_results = {}
        for source_name, encrypted_key in sources.items():
            if encrypted_key:
                try:
                    crypto_manager = CryptoManager()
                    decrypted = crypto_manager.decrypt_private_key(encrypted_key)
                    # 验证解密后的数据
                    keypair_bytes = bytes.fromhex(decrypted)
                    keypair = Keypair.from_bytes(keypair_bytes)
                    test_results[source_name] = {
                        'can_decrypt': True,
                        'address': str(keypair.pubkey())
                    }
                except Exception as e:
                    test_results[source_name] = {
                        'can_decrypt': False,
                        'error': str(e)
                    }
            else:
                test_results[source_name] = {
                    'can_decrypt': False,
                    'error': 'No key found'
                }

        return jsonify({
            'success': True,
            'sources': {k: bool(v) for k, v in sources.items()},
            'addresses': addresses,
            'test_results': test_results
        })

    except Exception as e:
        logger.error(f"获取平台私钥状态失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取平台私钥状态失败',
            'message': str(e)
        }), 500

@system_config_bp.route('/encryption-test', methods=['POST'])
@admin_required
def test_encryption():
    """测试加密解密功能"""
    try:
        data = request.get_json()
        test_string = data.get('test_string', 'test_data_123')

        crypto_manager = CryptoManager()

        # 测试加密
        encrypted = crypto_manager.encrypt_private_key(test_string)

        # 测试解密
        decrypted = crypto_manager.decrypt_private_key(encrypted)

        success = decrypted == test_string

        return jsonify({
            'success': success,
            'test_string': test_string,
            'encrypted': encrypted[:50] + '...',  # 只显示前50个字符
            'decrypted': decrypted,
            'match': success,
            'crypto_password_configured': bool(current_app.config.get('CRYPTO_PASSWORD'))
        })

    except Exception as e:
        logger.error(f"加密测试失败: {e}")
        return jsonify({
            'success': False,
            'error': '加密测试失败',
            'message': str(e)
        }), 500