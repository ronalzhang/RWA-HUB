import os
from flask import jsonify, current_app, Blueprint, request
from app.blockchain.asset_service import AssetService
from app.blockchain.solana import SolanaClient
from app.blockchain.solana_service import execute_transfer_transaction, validate_solana_address
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

@service_bp.route('/config/payment_settings', methods=['GET'])
def get_payment_settings():
    """获取支付设置"""
    try:
        # 从配置中获取支付设置
        platform_fee_address = current_app.config.get('PLATFORM_FEE_ADDRESS', 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd')
        usdc_mint = current_app.config.get('SOLANA_USDC_MINT', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
        
        # 默认创建资产费用设置
        settings = {
            'platform_fee_address': platform_fee_address,
            'usdc_mint': usdc_mint,
            'creation_fee': {
                'amount': '0.01',
                'token': 'USDC'
            },
            'currency': 'USDC'
        }
        
        return jsonify(settings)
    except Exception as e:
        logger.error(f"获取支付设置失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取支付设置失败: {str(e)}'}), 500

@service_bp.route('/solana/execute_transfer_v2', methods=['POST'])
def execute_transfer_v2():
    """执行代币转账"""
    try:
        data = request.json
        logger.info(f"收到转账请求: {data}")
        
        # 验证必要参数
        required_fields = ['fromAddress', 'toAddress', 'amount', 'token']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'缺少必要参数: {field}'}), 400
        
        # 验证地址格式
        if not validate_solana_address(data['fromAddress']):
            return jsonify({'success': False, 'message': '发送方地址格式无效'}), 400
        if not validate_solana_address(data['toAddress']):
            return jsonify({'success': False, 'message': '接收方地址格式无效'}), 400
        
        # 验证金额
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'success': False, 'message': '转账金额必须大于0'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': '无效的转账金额'}), 400
        
        # 执行转账
        signature = execute_transfer_transaction(
            token_symbol=data['token'],
            from_address=data['fromAddress'],
            to_address=data['toAddress'],
            amount=amount
        )
        
        # 记录资产创建费用支付
        if data.get('purpose') == 'asset_creation' and data.get('metadata'):
            asset_symbol = data['metadata'].get('assetSymbol')
            if asset_symbol:
                logger.info(f"记录资产创建费用支付: {asset_symbol}")
                # 记录交易
                new_trade = Trade(
                    asset_symbol=asset_symbol,
                    buyer_address=data['fromAddress'],
                    seller_address=data['toAddress'],
                    amount=Decimal(str(amount)),
                    price=Decimal('1.0'),  # 单价为1 USDC
                    total=Decimal(str(amount)),
                    currency='USDC',
                    transaction_hash=signature,
                    status=TradeStatus.COMPLETED,
                    trade_type=TradeType.ASSET_CREATION_FEE,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_trade)
                db.session.commit()
        
        return jsonify({
            'success': True,
            'signature': signature,
            'message': '转账请求已提交'
        })
    except Exception as e:
        logger.error(f"执行转账失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'执行转账失败: {str(e)}'}), 500 