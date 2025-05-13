import os
from flask import jsonify, current_app, Blueprint, request
from app.blockchain.asset_service import AssetService
from app.blockchain.solana import SolanaClient
from . import service_bp  # 从__init__.py导入正确的蓝图

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