import os
from flask import jsonify, current_app, Blueprint, request
from app.blockchain.asset_service import AssetService
from app.blockchain.solana import SolanaClient

# 创建蓝图实例
service_bp = Blueprint('service', __name__)

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
        
        # 获取余额
        balance = solana_client.get_balance()
        
        # 检查余额是否足够
        threshold = float(os.environ.get('SOLANA_BALANCE_THRESHOLD', 0.1))
        is_sufficient = balance is not None and balance >= threshold
        
        return jsonify({
            'success': True,
            'balance': balance,
            'balance_sol': balance,
            'threshold': threshold,
            'is_sufficient': is_sufficient,
            'wallet_address': wallet_address,
            'network': solana_client.network_url,
            'readonly_mode': True,
            'transaction_capable': False
        })
    except Exception as e:
        current_app.logger.error(f"获取钱包状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'wallet_address': wallet_address
        }), 500

@service_bp.route('/wallet/token_balance')
def wallet_token_balance():
    """
    获取钱包的代币余额
    
    参数:
    - address: 钱包地址
    - token: 代币名称（例如USDC）
    """
    wallet_address = request.args.get('address')
    token = request.args.get('token', 'USDC')
    
    if not wallet_address:
        return jsonify({
            'success': False,
            'error': '未提供钱包地址'
        }), 400
    
    try:
        # 根据token获取相应的代币地址
        if token == 'USDC':
            token_mint_address = current_app.config.get('SOLANA_USDC_MINT')
        else:
            token_mint_address = token  # 如果提供的是代币地址，直接使用
        
        # 获取代币余额
        balance = AssetService.get_token_balance(wallet_address, token_mint_address)
        
        return jsonify({
            'success': True,
            'balance': balance,
            'token': token,
            'wallet_address': wallet_address
        })
    except Exception as e:
        current_app.logger.error(f"获取代币余额失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'wallet_address': wallet_address
        }), 500

@service_bp.route('/user/assets')
def get_user_assets():
    """
    获取用户的资产列表
    
    参数:
    - address: 钱包地址
    - wallet_type: 钱包类型
    """
    wallet_address = request.args.get('address')
    wallet_type = request.args.get('wallet_type', 'metamask')
    
    if not wallet_address:
        return jsonify({
            'success': False,
            'error': '未提供钱包地址'
        }), 400
    
    try:
        # 获取用户资产
        assets = AssetService.get_user_assets(wallet_address, wallet_type)
        
        return jsonify({
            'success': True,
            'assets': assets,
            'wallet_address': wallet_address
        })
    except Exception as e:
        current_app.logger.error(f"获取用户资产失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'wallet_address': wallet_address
        }), 500 