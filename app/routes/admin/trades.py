"""
交易管理模块
"""

from flask import render_template, jsonify, request, current_app
from sqlalchemy import func, or_, desc
from datetime import datetime, timedelta
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required
from app.extensions import db
from app.models.trade import Trade, TradeStatus
from app.models.asset import Asset
from app.models.user import User


@admin_bp.route('/trades')
@admin_page_required
def trades_page():
    """交易管理页面"""
    return render_template('admin_v2/trades.html')

# V2版本API路由
@admin_bp.route('/v2/api/trades', methods=['GET'])
@api_admin_required
def trades_list_v2():
    """获取交易列表 - V2兼容版本"""
    return get_trades_list()

@admin_bp.route('/v2/api/trades/stats', methods=['GET'])
@api_admin_required
def trades_stats_v2():
    """获取交易统计 - V2兼容版本"""
    return get_trades_stats()

@admin_bp.route('/v2/api/trades/<int:trade_id>/status', methods=['PUT'])
@api_admin_required
def update_trade_status_v2(trade_id):
    """更新交易状态 - V2兼容版本"""
    return update_trade_status(trade_id)

@admin_bp.route('/v2/api/trades/export', methods=['GET'])
@api_admin_required
def export_trades_v2():
    """导出交易数据 - V2兼容版本"""
    return export_trades()

# 原有API路由
@admin_bp.route('/api/trades', methods=['GET'])
@api_admin_required
def get_trades_list():
    """获取交易列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status', '')
        trade_type = request.args.get('type', '')
        time_range = request.args.get('time_range', '')
        search = request.args.get('search', '')
        
        # 构建查询
        query = Trade.query
        
        # 状态过滤
        if status:
            if hasattr(TradeStatus, status.upper()):
                query = query.filter(Trade.status == getattr(TradeStatus, status.upper()).value)
        
        # 类型过滤
        if trade_type:
            query = query.filter(Trade.trade_type == trade_type)
        
        # 时间范围过滤
        if time_range:
            now = datetime.utcnow()
            if time_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(Trade.created_at >= start_date)
            elif time_range == 'week':
                start_date = now - timedelta(days=7)
                query = query.filter(Trade.created_at >= start_date)
            elif time_range == 'month':
                start_date = now - timedelta(days=30)
                query = query.filter(Trade.created_at >= start_date)
        
        # 搜索条件
        if search:
            query = query.join(Asset, Trade.asset_id == Asset.id, isouter=True).filter(
                or_(
                    Trade.buyer_address.ilike(f'%{search}%'),
                    Trade.seller_address.ilike(f'%{search}%'),
                    Trade.tx_hash.ilike(f'%{search}%'),
                    Asset.name.ilike(f'%{search}%'),
                    Asset.token_symbol.ilike(f'%{search}%')
                )
            )
        
        # 计算总数
        total = query.count()
        total_pages = (total + limit - 1) // limit
        
        # 获取分页数据
        trades = query.order_by(Trade.created_at.desc()) \
            .offset((page - 1) * limit) \
            .limit(limit) \
            .all()
        
        # 格式化响应数据
        trades_list = []
        for trade in trades:
            trade_dict = {
                'id': trade.id,
                'asset_id': trade.asset_id,
                'asset_name': trade.asset.name if trade.asset else '未知资产',
                'token_symbol': trade.asset.token_symbol if trade.asset else '-',
                'buyer_address': trade.buyer_address,
                'seller_address': trade.seller_address,
                'trader_address': trade.buyer_address,  # 兼容前端
                'token_amount': trade.token_amount,
                'price': float(trade.price) if trade.price else 0,
                'total': float(trade.total) if trade.total else 0,
                'amount': trade.token_amount,  # 兼容前端
                'status': trade.status,
                'trade_type': getattr(trade, 'trade_type', 'buy'),
                'type': 'buy',  # 兼容前端，简化为买入
                'tx_hash': trade.tx_hash,
                'created_at': trade.created_at.isoformat()
            }
            trades_list.append(trade_dict)
        
        return jsonify({
            'items': trades_list,
            'total': total,
            'pages': total_pages,
            'page': page,
            'limit': limit
        })
    
    except Exception as e:
        current_app.logger.error(f"获取交易列表失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/trades/stats', methods=['GET'])
@api_admin_required
def get_trades_stats():
    """获取交易统计数据"""
    try:
        # 总交易数
        total_trades = Trade.query.count()
        
        # 已完成交易数
        completed_trades = Trade.query.filter(Trade.status == TradeStatus.COMPLETED.value).count()
        
        # 待处理交易数
        pending_trades = Trade.query.filter(Trade.status == TradeStatus.PENDING.value).count()
        
        # 失败交易数
        failed_trades = Trade.query.filter(Trade.status == TradeStatus.FAILED.value).count()
        
        # 总交易金额
        total_volume = db.session.query(func.sum(Trade.total)).filter(
            Trade.status == TradeStatus.COMPLETED.value
        ).scalar() or 0
        
        # 今日交易量
        today = datetime.utcnow().date()
        today_volume = db.session.query(func.sum(Trade.total)).filter(
            Trade.status == TradeStatus.COMPLETED.value,
            func.date(Trade.created_at) == today
        ).scalar() or 0
        
        return jsonify({
            'totalTrades': total_trades,
            'completedTrades': completed_trades,
            'pendingTrades': pending_trades,
            'failedTrades': failed_trades,
            'totalVolume': float(total_volume),
            'todayVolume': float(today_volume)
        })
    
    except Exception as e:
        current_app.logger.error(f"获取交易统计失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/trades/<int:trade_id>/status', methods=['PUT'])
@api_admin_required
def update_trade_status(trade_id):
    """更新交易状态"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': '缺少状态参数'}), 400
        
        trade = Trade.query.get_or_404(trade_id)
        new_status = data['status']
        
        # 验证状态值
        valid_statuses = ['pending', 'completed', 'failed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'error': '无效的状态值'}), 400
        
        # 转换为枚举值
        if new_status == 'pending':
            trade.status = TradeStatus.PENDING.value
        elif new_status == 'completed':
            trade.status = TradeStatus.COMPLETED.value
        elif new_status == 'failed':
            trade.status = TradeStatus.FAILED.value
        elif new_status == 'cancelled':
            trade.status = TradeStatus.CANCELLED.value
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '状态更新成功'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新交易状态失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/trades/export', methods=['GET'])
@api_admin_required
def export_trades():
    """导出交易数据"""
    try:
        import csv
        import io
        from flask import make_response
        
        # 获取所有交易数据
        trades = Trade.query.join(Asset, Trade.asset_id == Asset.id, isouter=True) \
            .order_by(Trade.created_at.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        writer.writerow([
            'ID', '资产名称', 'Token符号', '买方地址', '卖方地址', 
            '交易数量', '价格', '总金额', '状态', '交易哈希', '创建时间'
        ])
        
        # 写入数据行
        for trade in trades:
            status_text = {
                TradeStatus.PENDING.value: '待处理',
                TradeStatus.COMPLETED.value: '已完成',
                TradeStatus.FAILED.value: '失败',
                TradeStatus.CANCELLED.value: '已取消'
            }.get(trade.status, '未知状态')
            
            writer.writerow([
                trade.id,
                trade.asset.name if trade.asset else '未知资产',
                trade.asset.token_symbol if trade.asset else '-',
                trade.buyer_address,
                trade.seller_address,
                trade.token_amount,
                float(trade.price) if trade.price else 0,
                float(trade.total) if trade.total else 0,
                status_text,
                trade.tx_hash or '',
                trade.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=trades_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"导出交易数据失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500 