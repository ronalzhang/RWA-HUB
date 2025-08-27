"""
交易历史和实时数据API
提供资产交易历史和实时数据接口
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, and_
from app.models import Trade, Asset, User
from app.extensions import db
from app.utils.error_handler import create_error_response
from app.utils.decorators import api_endpoint

logger = logging.getLogger(__name__)

# 创建交易API蓝图
trades_api_bp = Blueprint('trades_api', __name__, url_prefix='/api/trades')

@trades_api_bp.route('/asset/<int:asset_id>/trades/history', methods=['GET'])
@api_endpoint(log_calls=True)
def get_asset_trade_history(asset_id):
    """获取资产交易历史"""
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 限制每页数量
        per_page = min(per_page, 100)
        
        # 检查资产是否存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return create_error_response('ASSET_NOT_FOUND', f'资产 {asset_id} 不存在')
        
        # 查询交易历史
        trades_query = Trade.query.filter(
            Trade.asset_id == asset_id,
            Trade.status.in_(['completed', 'confirmed'])
        ).order_by(desc(Trade.created_at))
        
        # 分页
        trades_pagination = trades_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # 格式化交易数据
        trades_data = []
        for trade in trades_pagination.items:
            trades_data.append({
                'id': trade.id,
                'amount': float(trade.amount) if trade.amount else 0,
                'price': float(trade.price) if trade.price else 0,
                'total_value': float(trade.total) if trade.total else 0,
                'status': trade.status,
                'created_at': trade.created_at.isoformat() if trade.created_at else None,
                'updated_at': trade.status_updated_at.isoformat() if trade.status_updated_at else None,
                'tx_hash': trade.tx_hash,
                'user_address': trade.trader_address,
                'trade_type': getattr(trade, 'type', 'buy')
            })
        
        return jsonify({
            'success': True,
            'data': {
                'trades': trades_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': trades_pagination.total,
                    'pages': trades_pagination.pages,
                    'has_next': trades_pagination.has_next,
                    'has_prev': trades_pagination.has_prev
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取资产 {asset_id} 交易历史失败: {e}", exc_info=True)
        return create_error_response('INTERNAL_ERROR', '获取交易历史失败')

@trades_api_bp.route('/asset/<int:asset_id>/data/realtime', methods=['GET'])
@api_endpoint(log_calls=True)
def get_asset_realtime_data(asset_id):
    """获取资产实时数据"""
    try:
        # 检查资产是否存在
        asset = Asset.query.get(asset_id)
        if not asset:
            return create_error_response('ASSET_NOT_FOUND', f'资产 {asset_id} 不存在')
        
        # 获取最新交易数据
        latest_trade = Trade.query.filter(
            Trade.asset_id == asset_id,
            Trade.status.in_(['completed', 'confirmed'])
        ).order_by(desc(Trade.created_at)).first()
        
        # 计算24小时交易统计
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        daily_stats = db.session.query(
            db.func.count(Trade.id).label('trade_count'),
            db.func.sum(Trade.amount).label('total_amount'),
            db.func.sum(Trade.total).label('total_value')
        ).filter(
            Trade.asset_id == asset_id,
            Trade.status.in_(['completed', 'confirmed']),
            Trade.created_at >= yesterday
        ).first()
        
        # 获取当前价格（从最新交易或资产默认价格）
        current_price = float(latest_trade.price) if latest_trade and latest_trade.price else float(asset.token_price or 0)
        
        # 构建实时数据
        realtime_data = {
            'asset_id': asset_id,
            'asset_symbol': asset.token_symbol,
            'current_price': current_price,
            'last_trade_time': latest_trade.created_at.isoformat() if latest_trade else None,
            'daily_stats': {
                'trade_count': daily_stats.trade_count or 0,
                'total_amount': float(daily_stats.total_amount or 0),
                'total_value': float(daily_stats.total_value or 0)
            },
            'asset_info': {
                'total_supply': float(asset.token_supply or 0),
                'available_supply': float(asset.remaining_supply or 0),
                'market_cap': float(asset.token_supply or 0) * current_price if asset.token_supply else 0
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': realtime_data
        })
        
    except Exception as e:
        logger.error(f"获取资产 {asset_id} 实时数据失败: {e}", exc_info=True)
        return create_error_response('INTERNAL_ERROR', '获取实时数据失败')

@trades_api_bp.route('/', methods=['GET'])
@api_endpoint(log_calls=True)
def get_trades():
    """获取交易列表（通用接口）"""
    try:
        # 获取查询参数
        asset_id = request.args.get('asset_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        # 限制每页数量
        per_page = min(per_page, 100)
        
        # 构建查询
        query = Trade.query
        
        if asset_id:
            query = query.filter(Trade.asset_id == asset_id)
        
        if status:
            query = query.filter(Trade.status == status)
        else:
            # 默认只返回已完成的交易
            query = query.filter(Trade.status.in_(['completed', 'confirmed']))
        
        # 排序
        query = query.order_by(desc(Trade.created_at))
        
        # 分页
        trades_pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # 格式化数据
        trades_data = []
        for trade in trades_pagination.items:
            asset = Asset.query.get(trade.asset_id) if trade.asset_id else None
            
            trades_data.append({
                'id': trade.id,
                'asset_id': trade.asset_id,
                'asset_symbol': asset.token_symbol if asset else None,
                'amount': float(trade.amount) if trade.amount else 0,
                'price': float(trade.price) if trade.price else 0,
                'total_value': float(trade.total) if trade.total else 0,
                'status': trade.status,
                'created_at': trade.created_at.isoformat() if trade.created_at else None,
                'updated_at': trade.status_updated_at.isoformat() if trade.status_updated_at else None,
                'tx_hash': trade.tx_hash,
                'user_address': trade.trader_address,
                'trade_type': getattr(trade, 'type', 'buy')
            })
        
        return jsonify({
            'success': True,
            'data': {
                'trades': trades_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': trades_pagination.total,
                    'pages': trades_pagination.pages,
                    'has_next': trades_pagination.has_next,
                    'has_prev': trades_pagination.has_prev
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取交易列表失败: {e}", exc_info=True)
        return create_error_response('INTERNAL_ERROR', '获取交易列表失败')

@trades_api_bp.route('/user/<string:user_address>', methods=['GET'])
@api_endpoint(log_calls=True)
def get_user_trades(user_address):
    """获取指定用户的交易历史"""
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 限制每页数量
        per_page = min(per_page, 100)
        
        # 验证用户地址
        if not user_address:
            return create_error_response('VALIDATION_ERROR', '用户地址不能为空')
        
        # 查询交易历史
        trades_query = Trade.query.filter(
            Trade.trader_address == user_address
        ).order_by(desc(Trade.created_at))
        
        # 分页
        trades_pagination = trades_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # 格式化数据
        trades_data = []
        for trade in trades_pagination.items:
            asset = Asset.query.get(trade.asset_id) if trade.asset_id else None
            
            trades_data.append({
                'id': trade.id,
                'asset_id': trade.asset_id,
                'asset_symbol': asset.token_symbol if asset else None,
                'asset_name': asset.name if asset else None,
                'amount': float(trade.amount) if trade.amount else 0,
                'price': float(trade.price) if trade.price else 0,
                'total_value': float(trade.total) if trade.total else 0,
                'status': trade.status,
                'created_at': trade.created_at.isoformat() if trade.created_at else None,
                'updated_at': trade.status_updated_at.isoformat() if trade.status_updated_at else None,
                'tx_hash': trade.tx_hash,
                'trade_type': getattr(trade, 'type', 'buy')
            })
        
        return jsonify({
            'success': True,
            'data': {
                'trades': trades_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': trades_pagination.total,
                    'pages': trades_pagination.pages,
                    'has_next': trades_pagination.has_next,
                    'has_prev': trades_pagination.has_prev
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户 {user_address} 交易历史失败: {e}", exc_info=True)
        return create_error_response('INTERNAL_ERROR', '获取用户交易历史失败')

# =================================================================
# V3 购买流程 API (重构)
# =================================================================

@trades_api_bp.route('/v3/create', methods=['POST'])
@api_endpoint(log_calls=True, measure_perf=True)
def create_purchase_v3():
    """
    创建购买交易 V3 - 重构版
    第一步: 验证输入, 创建数据库记录, 构建并返回待签名交易
    """
    try:
        # 1. 获取和验证输入
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_INPUT', '请求体不能为空')

        wallet_address = data.get('wallet_address')
        asset_id = data.get('asset_id')
        amount = data.get('amount')

        if not all([wallet_address, asset_id, amount]):
            return create_error_response('MISSING_PARAMETERS', '缺少必要参数: wallet_address, asset_id, amount')

        # 2. 引入新的TradeService (将在后续步骤中重构)
        from app.services.trade_service_v3 import TradeServiceV3
        
        # 3. 调用服务层来处理业务逻辑
        result = TradeServiceV3.create_purchase(
            wallet_address=wallet_address,
            asset_id=asset_id,
            amount=amount
        )
        
        if not result['success']:
            return create_error_response(result.get('error_code', 'TRADE_CREATION_FAILED'), result.get('message'))

        logger.info(f"[V3] 成功创建购买交易: 用户={wallet_address}, 资产={asset_id}, 数量={amount}")
        return jsonify(result), 201

    except Exception as e:
        logger.error(f"[V3] 创建购买交易失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'创建购买交易失败: {str(e)}')


@trades_api_bp.route('/v3/confirm', methods=['POST'])
@api_endpoint(log_calls=True, measure_perf=True)
def confirm_purchase_v3():
    """
    确认购买交易 V3 - 重构版
    第二步: 接收签名, 验证链上交易, 更新数据库状态
    """
    try:
        # 1. 获取和验证输入
        data = request.get_json()
        if not data:
            return create_error_response('INVALID_INPUT', '请求体不能为空')

        trade_id = data.get('trade_id')
        tx_hash = data.get('tx_hash')

        if not all([trade_id, tx_hash]):
            return create_error_response('MISSING_PARAMETERS', '缺少必要参数: trade_id, tx_hash')

        # 2. 引入新的TradeService (将在后续步骤中重构)
        from app.services.trade_service_v3 import TradeServiceV3

        # 3. 调用服务层确认交易
        result = TradeServiceV3.confirm_purchase(
            trade_id=trade_id,
            tx_hash=tx_hash
        )

        if not result['success']:
            return create_error_response(result.get('error_code', 'TRADE_CONFIRMATION_FAILED'), result.get('message'))

        logger.info(f"[V3] 成功确认购买交易: 交易ID={trade_id}, 哈希={tx_hash}")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"[V3] 确认购买交易失败: {str(e)}", exc_info=True)
        return create_error_response('INTERNAL_SERVER_ERROR', f'确认购买交易失败: {str(e)}')
