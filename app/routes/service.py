import os
from flask import jsonify, current_app, Blueprint, request
from app.blockchain.asset_service import AssetService
from app.blockchain.solana import SolanaClient
from app.blockchain.solana_service import validate_solana_address, check_transaction
from . import service_bp  # 从__init__.py导入正确的蓝图
import json
import logging
import traceback
from decimal import Decimal
from datetime import datetime
from app.extensions import db
from app.models import Asset, Trade
from app.models.trade import TradeStatus, TradeType

# 获取日志记录器
logger = logging.getLogger(__name__)

@service_bp.route('/wallet/status')
def service_wallet_status():
    """
    获取服务钱包状态
    """
    return jsonify(AssetService.get_service_wallet_status())


@service_bp.route('/wallet/status/<wallet_address>')
def service_wallet_status_with_address(wallet_address):
    """
    获取指定钱包地址的状态
    
    Args:
        wallet_address: Solana钱包地址
    """
    # 检查请求中是否包含钱包地址
    if not wallet_address:
        return jsonify({
            'success': False,
            'error': '未提供钱包地址'
        }), 400
        
    try:
        # 初始化Solana客户端
        solana_client = SolanaClient(wallet_address=wallet_address)
        
        # 获取钱包状态
        status = solana_client.get_wallet_status()
        
        # 添加成功标志
        status['success'] = True
        
        return jsonify(status)
    except Exception as e:
        current_app.logger.error(f"获取钱包状态出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@service_bp.route('/wallet/token_balance')
def wallet_token_balance():
    """
    获取钱包的代币余额
    
    Query参数:
        address: 钱包地址
        token: 代币符号（例如USDC）
    """
    address = request.args.get('address')
    token = request.args.get('token', 'USDC')  # 默认为USDC
    
    if not address:
        return jsonify({
            'success': False,
            'error': '未提供钱包地址'
        }), 400
    
    try:
        # 对于USDC代币，调用AssetService的get_token_balance方法
        if token.upper() == 'USDC':
            # 根据环境使用相应的代币地址
            token_mint_address = current_app.config.get('SOLANA_USDC_MINT_ADDRESS')
            if not token_mint_address:
                token_mint_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # Solana USDC默认地址
                
            balance = AssetService.get_token_balance(address, token_mint_address)
            
            return jsonify({
                'success': True,
                'balance': str(balance),
                'symbol': token.upper()
            })
        else:
            # 其他代币的处理逻辑
            return jsonify({
                'success': False,
                'error': f'不支持的代币类型: {token}'
            }), 400
    except Exception as e:
        current_app.logger.error(f"获取代币余额出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@service_bp.route('/user/assets')
def get_user_assets():
    """
    获取用户的资产列表
    
    Query参数:
        address: 钱包地址
        wallet_type: 钱包类型（默认为metamask）
    """
    address = request.args.get('address')
    wallet_type = request.args.get('wallet_type', 'metamask')
    
    if not address:
        return jsonify({
            'success': False,
            'error': '未提供钱包地址'
        }), 400
    
    try:
        # 调用AssetService获取用户资产
        assets = AssetService.get_user_assets(address, wallet_type)
        
        return jsonify({
            'success': True,
            'assets': assets
        })
    except Exception as e:
        current_app.logger.error(f"获取用户资产出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 

@service_bp.route('/wallet/commission_balance')
def wallet_commission_balance():
    """
    获取钱包的分佣余额
    
    Query参数:
        address: 钱包地址
    """
    address = request.args.get('address')
    
    if not address:
        return jsonify({
            'success': False,
            'error': '未提供钱包地址'
        }), 400
    
    try:
        # 调用AssetService的get_commission_balance方法
        commission_balance = AssetService.get_commission_balance(address)
        
        return jsonify({
            'success': True,
            'balance': str(commission_balance),
            'symbol': 'USDC'
        })
        
    except Exception as e:
        current_app.logger.error(f"获取分佣余额出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@service_bp.route('/wallet/usdc_balance')
def wallet_usdc_balance():
    """
    获取钱包的USDC余额（服务器代理方式）
    
    Query参数:
        address: 钱包地址
        network: 网络类型 (ethereum/solana)
    """
    address = request.args.get('address')
    network = request.args.get('network', 'ethereum')
    
    if not address:
        return jsonify({
            'success': False,
            'error': '未提供钱包地址'
        }), 400
    
    try:
        # 使用服务器代理获取USDC余额
        if network == 'ethereum':
            balance = AssetService.get_ethereum_usdc_balance(address)
        elif network == 'solana':
            balance = AssetService.get_solana_usdc_balance(address)
        else:
            return jsonify({
                'success': False,
                'error': '不支持的网络类型'
            }), 400
        
        return jsonify({
            'success': True,
            'balance': str(balance),
            'symbol': 'USDC',
            'network': network,
            'cached_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"获取USDC余额出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'balance': '0'  # 出错时返回0余额
        }), 200  # 返回200状态码，避免前端报错

@service_bp.route('/config/payment_settings', methods=['GET'])
def get_payment_settings():
    """获取支付设置"""
    try:
        from app.utils.config_manager import ConfigManager
        
        # 使用统一的配置管理器获取支付设置
        settings = ConfigManager.get_payment_settings()
        
        current_app.logger.info(f"返回支付设置: {settings}")
        return jsonify(settings)
    except Exception as e:
        logger.error(f"获取支付设置失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取支付设置失败: {str(e)}'}), 500



@service_bp.route('/blockchain/solana/check-transaction', methods=['GET'])
def check_solana_transaction():
    """检查Solana交易状态"""
    try:
        # 获取交易签名
        signature = request.args.get('signature')
        if not signature:
            return jsonify({'success': False, 'message': '缺少交易签名参数'}), 400
        
        logger.info(f"检查Solana交易状态: {signature}")
        
        # 调用检查函数
        status = check_transaction(signature)
        
        # 添加成功标志
        if 'error' not in status:
            status['success'] = True
        else:
            status['success'] = False
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"检查交易状态失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'检查交易状态失败: {str(e)}'}), 500 

@service_bp.route('/user/register_wallet', methods=['POST'])
def register_wallet_user():
    """
    钱包连接时自动注册/更新用户信息
    
    POST数据:
        address: 钱包地址
        wallet_type: 钱包类型
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '未提供数据'
            }), 400
        
        address = data.get('address')
        wallet_type = data.get('wallet_type', 'ethereum')
        
        if not address:
            return jsonify({
                'success': False,
                'error': '未提供钱包地址'
            }), 400
        
        # 调用AssetService注册用户
        user_info = AssetService.register_wallet_user(address, wallet_type)
        
        return jsonify({
            'success': True,
            'user': user_info,
            'message': '用户注册/更新成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"注册钱包用户出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 