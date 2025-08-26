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