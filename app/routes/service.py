import os
from flask import jsonify, current_app, Blueprint
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