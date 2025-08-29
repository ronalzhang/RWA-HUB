"""
交易V3 API - 修复缺失的交易创建和确认端点
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from app.models import Trade, Asset
from app.extensions import db
from app.utils.error_handler import create_error_response
from app.utils.decorators import api_endpoint
from decimal import Decimal
import base64

logger = logging.getLogger(__name__)

# 创建交易V3 API蓝图
trade_confirm_bp = Blueprint('trade_confirm', __name__, url_prefix='/api/trades')

@trade_confirm_bp.route('/v3/create', methods=['POST'])
@api_endpoint(log_calls=True)
def create_trade_v3():
    """创建交易 - V3版本"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_REQUEST', '请求数据为空')
        
        asset_id = data.get('asset_id')
        amount = data.get('amount')
        wallet_address = data.get('wallet_address')
        
        if not asset_id:
            return create_error_response('VALIDATION_ERROR', '缺少资产ID')
        
        if not amount or amount <= 0:
            return create_error_response('INVALID_AMOUNT', '无效的购买数量')
        
        if not wallet_address:
            return create_error_response('VALIDATION_ERROR', '缺少钱包地址')
        
        # 查找资产
        asset = Asset.query.get(asset_id)
        if not asset:
            return create_error_response('ASSET_NOT_FOUND', f'资产 {asset_id} 不存在')
        
        # 验证钱包地址格式
        from app.utils.validation_utils import ValidationUtils
        if not ValidationUtils.validate_wallet_address(wallet_address):
            return create_error_response('VALIDATION_ERROR', '无效的钱包地址格式')
        
        # 标准化地址
        normalized_address = ValidationUtils.normalize_address(wallet_address)
        
        # 创建交易记录
        trade = Trade(
            asset_id=asset_id,
            type='buy',  # 设置交易类型
            amount=int(amount),  # Trade模型期望整数
            price=float(asset.price_per_token),
            total=float(amount) * float(asset.price_per_token),
            trader_address=normalized_address,
            status='pending'
        )
        
        db.session.add(trade)
        db.session.commit()
        
        # 创建模拟的交易数据（实际应该调用区块链服务）
        transaction_data = {
            'trade_id': trade.id,
            'asset_id': asset_id,
            'amount': amount,
            'wallet_address': normalized_address
        }
        
        # 模拟序列化交易（实际应该是真实的区块链交易）
        transaction_base64 = base64.b64encode(str(transaction_data).encode()).decode()
        
        logger.info(f"交易 {trade.id} 创建成功")
        
        return jsonify({
            'success': True,
            'message': '交易创建成功',
            'trade_id': trade.id,
            'transaction': transaction_base64
        })
        
    except Exception as e:
        logger.error(f"创建交易失败: {e}", exc_info=True)
        db.session.rollback()
        return create_error_response('INTERNAL_ERROR', f'创建交易失败: {str(e)}')

@trade_confirm_bp.route('/v3/confirm', methods=['POST'])
@api_endpoint(log_calls=True)
def confirm_trade_v3():
    """确认交易 - V3版本"""
    try:
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_REQUEST', '请求数据为空')
        
        trade_id = data.get('trade_id')
        tx_hash = data.get('tx_hash')
        
        if not trade_id:
            return create_error_response('VALIDATION_ERROR', '缺少交易ID')
        
        if not tx_hash:
            return create_error_response('VALIDATION_ERROR', '缺少交易哈希')
        
        # 查找交易
        trade = Trade.query.get(trade_id)
        if not trade:
            return create_error_response('TRADE_NOT_FOUND', f'交易 {trade_id} 不存在')
        
        # 更新交易状态
        trade.tx_hash = tx_hash
        trade.status = 'completed'
        trade.status_updated_at = db.func.now()
        
        db.session.commit()
        
        logger.info(f"交易 {trade_id} 确认成功，哈希: {tx_hash}")
        
        return jsonify({
            'success': True,
            'message': '交易确认成功',
            'data': {
                'trade_id': trade_id,
                'tx_hash': tx_hash,
                'status': 'completed'
            }
        })
        
    except Exception as e:
        logger.error(f"确认交易失败: {e}", exc_info=True)
        db.session.rollback()
        return create_error_response('INTERNAL_ERROR', '确认交易失败')