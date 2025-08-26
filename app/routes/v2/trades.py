"""
交易API V2 - 提供清晰、统一的资产交易接口
"""
import logging
from flask import Blueprint, request, jsonify
from app.services.trade_service import TradeService
from app.utils.error_handler import AppError, error_handler
from app.utils.auth import wallet_address_required

logger = logging.getLogger(__name__)

trades_v2_bp = Blueprint('trades_v2_api', __name__, url_prefix='/api/v2/trades')

@trades_v2_bp.route('/create', methods=['POST'])
@wallet_address_required
def create_purchase_v2(user_address: str):
    """
    创建购买交易的V2端点。
    接收资产ID和数量，返回待签名的交易信息。
    """
    try:
        data = request.get_json()
        if not data:
            raise AppError("INVALID_INPUT", "请求体不能为空。")

        asset_id = data.get('asset_id')
        amount = data.get('amount')

        trade_service = TradeService()
        result = trade_service.create_purchase(user_address, asset_id, amount)

        return jsonify(result), 201

    except AppError as e:
        return error_handler(e)
    except Exception as e:
        logger.error(f"创建V2购买交易时发生未知错误: {e}", exc_info=True)
        return error_handler(AppError("INTERNAL_ERROR", "发生未知错误，请稍后重试。"))

@trades_v2_bp.route('/confirm', methods=['POST'])
@wallet_address_required
def confirm_purchase_v2(user_address: str):
    """
    确认购买交易的V2端点。
    接收交易ID和链上交易哈希，完成交易确认流程。
    """
    try:
        data = request.get_json()
        if not data:
            raise AppError("INVALID_INPUT", "请求体不能为空。")

        trade_id = data.get('trade_id')
        tx_hash = data.get('tx_hash')

        trade_service = TradeService()
        result = trade_service.confirm_purchase(trade_id, tx_hash)

        return jsonify(result), 200

    except AppError as e:
        return error_handler(e)
    except Exception as e:
        logger.error(f"确认V2购买交易时发生未知错误: {e}", exc_info=True)
        return error_handler(AppError("INTERNAL_ERROR", "发生未知错误，请稍后重试。"))
