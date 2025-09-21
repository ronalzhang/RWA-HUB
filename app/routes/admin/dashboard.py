"""
仪表板管理模块
"""

from flask import render_template, jsonify, current_app, request
from sqlalchemy import func
from datetime import datetime, timedelta
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required
from app.extensions import db
from app.models.asset import Asset
from app.models.trade import Trade, TradeStatus
from app.models.user import User


@admin_bp.route('/dashboard')
@admin_page_required  
def dashboard():
    """仪表板页面"""
    return render_template('admin_v2/dashboard.html')


@admin_bp.route('/')
@admin_page_required
def admin_index():
    """管理后台首页"""
    return render_template('admin_v2/dashboard.html')


# 添加V2版本的API路由兼容性
@admin_bp.route('/v2/api/dashboard/stats')
@api_admin_required
def dashboard_stats_v2():
    """仪表板统计数据 - V2兼容版本"""
    return get_dashboard_stats()


@admin_api_bp.route('/dashboard/stats')
@api_admin_required
def dashboard_stats_api():
    """仪表板统计数据 - 新版API"""
    return get_dashboard_stats()


# 添加趋势数据API
@admin_bp.route('/v2/api/dashboard/trends')
@api_admin_required
def dashboard_trends_v2():
    """仪表板趋势数据 - V2兼容版本"""
    return get_dashboard_trends()


@admin_api_bp.route('/dashboard/trends')
@api_admin_required
def dashboard_trends_api():
    """仪表板趋势数据 - 新版API"""
    return get_dashboard_trends()


# 添加最近交易API
@admin_bp.route('/v2/api/dashboard/recent-trades')
@api_admin_required
def dashboard_recent_trades_v2():
    """最近交易数据 - V2兼容版本"""
    return get_recent_trades()


@admin_api_bp.route('/dashboard/recent-trades')
@api_admin_required
def dashboard_recent_trades_api():
    """最近交易数据 - 新版API"""
    return get_recent_trades()


# 添加资产类型统计API
@admin_bp.route('/v2/api/asset-type-stats')
@api_admin_required
def asset_type_stats_v2():
    """资产类型统计 - V2兼容版本"""
    return get_asset_type_stats()


@admin_api_bp.route('/asset-type-stats')
@api_admin_required
def asset_type_stats_api():
    """资产类型统计 - 新版API"""
    return get_asset_type_stats()


def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        # 获取今天的日期
        today = datetime.utcnow().date()
        
        # 获取用户统计
        total_users = User.query.count()
        new_users_today = User.query.filter(
            func.date(User.created_at) == today
        ).count()
        
        # 获取资产统计
        total_assets = Asset.query.filter(Asset.deleted_at.is_(None)).count()
        total_asset_value = db.session.query(func.sum(Asset.total_value)).filter(
            Asset.status == 2  # 只统计已审核通过的资产
        ).scalar() or 0
        
        # 获取交易统计
        total_trades = Trade.query.count()
        completed_trades = Trade.query.filter(Trade.status == TradeStatus.COMPLETED.value).count()
        
        # 获取交易金额统计
        total_trade_volume = db.session.query(func.sum(Trade.total)).filter(
            Trade.status == TradeStatus.COMPLETED.value
        ).scalar() or 0
        
        # 获取今日交易量
        today_trade_volume = db.session.query(func.sum(Trade.total)).filter(
            Trade.status == TradeStatus.COMPLETED.value,
            func.date(Trade.created_at) == today
        ).scalar() or 0
        
        # 计算平均交易价值
        average_trade_value = 0
        if completed_trades > 0:
            average_trade_value = total_trade_volume / completed_trades
        
        # 返回前端期望的数据格式
        return jsonify({
            'total_users': total_users,
            'new_users_today': new_users_today,
            'total_assets': total_assets,
            'total_asset_value': float(total_asset_value),
            'total_trades': total_trades,
            'completed_trades': completed_trades,
            'total_volume': float(total_trade_volume),  # 前端期望的字段名
            'today_volume': float(today_trade_volume),  # 前端期望的字段名
            'average_trade_value': float(average_trade_value),  # 前端期望的字段名
            'total_trade_volume': float(total_trade_volume)  # 兼容字段
        })
        
    except Exception as e:
        current_app.logger.error(f"获取仪表板统计数据失败: {str(e)}")
        return jsonify({
            'error': '获取统计数据失败',
            'total_users': 0,
            'new_users_today': 0,
            'total_assets': 0,
            'total_asset_value': 0,
            'total_trades': 0,
            'completed_trades': 0,
            'total_volume': 0,
            'today_volume': 0,
            'average_trade_value': 0,
            'total_trade_volume': 0
        }), 500


def get_dashboard_trends():
    """获取仪表板趋势数据"""
    try:
        days = int(request.args.get('days', 30))
        if days not in [7, 30, 90]:
            days = 30
            
        # 获取用户增长趋势
        user_growth = get_user_growth_trend(days)
        
        # 获取交易量趋势
        trading_volume = get_trading_volume_trend(days)
        
        return jsonify({
            'user_growth': user_growth,
            'trading_volume': trading_volume
        })
        
    except Exception as e:
        current_app.logger.error(f'获取仪表盘趋势数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'user_growth': {'labels': [], 'values': []},
            'trading_volume': {'labels': [], 'values': []}
        })


def get_recent_trades():
    """获取最近交易数据"""
    try:
        limit = int(request.args.get('limit', 5))
        trades = Trade.query.order_by(Trade.created_at.desc()).limit(limit).all()
        
        return jsonify([{
            'id': trade.id,
            'asset': {
                'name': trade.asset.name if trade.asset else None,
                'token_symbol': trade.asset.token_symbol if trade.asset else None
            },
            'total_price': float(trade.total),
            'token_amount': trade.token_amount,
            'status': trade.status,
            'created_at': trade.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for trade in trades])
        
    except Exception as e:
        current_app.logger.error(f'获取最近交易数据失败: {str(e)}', exc_info=True)
        return jsonify([])


def get_asset_type_stats():
    """获取资产类型统计"""
    try:
        # 查询各类型资产数量
        asset_stats = db.session.query(
            Asset.asset_type,
            func.count(Asset.id).label('count')
        ).filter(Asset.status == 2).group_by(Asset.asset_type).all()
        
        # 资产类型映射
        type_names = {
            1: '房地产',
            2: '股权',
            3: '债券',
            4: '商品',
            5: '其他'
        }
        
        labels = []
        values = []
        
        for asset_type, count in asset_stats:
            labels.append(type_names.get(asset_type, f'类型{asset_type}'))
            values.append(count)
        
        return jsonify({
            'labels': labels,
            'values': values
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产类型统计失败: {str(e)}', exc_info=True)
        return jsonify({
            'labels': [],
            'values': []
        })


def get_user_growth_trend(days=30):
    """获取用户增长趋势"""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        # 查询每日新增用户数
        daily_users = db.session.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            func.date(User.created_at) >= start_date,
            func.date(User.created_at) <= end_date
        ).group_by(func.date(User.created_at)).all()
        
        # 创建完整的日期序列
        labels = []
        values = []
        user_dict = {str(date): count for date, count in daily_users}
        
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%m-%d'))
            values.append(user_dict.get(str(current_date), 0))
            current_date += timedelta(days=1)
        
        return {
            'labels': labels,
            'values': values
        }
        
    except Exception as e:
        current_app.logger.error(f'获取用户增长趋势失败: {str(e)}')
        return {'labels': [], 'values': []}


def get_trading_volume_trend(days=30):
    """获取交易量趋势"""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        # 查询每日交易量
        daily_volume = db.session.query(
            func.date(Trade.created_at).label('date'),
            func.sum(Trade.total).label('volume')
        ).filter(
            Trade.status == TradeStatus.COMPLETED.value,
            func.date(Trade.created_at) >= start_date,
            func.date(Trade.created_at) <= end_date
        ).group_by(func.date(Trade.created_at)).all()
        
        # 创建完整的日期序列
        labels = []
        values = []
        volume_dict = {str(date): float(volume or 0) for date, volume in daily_volume}
        
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%m-%d'))
            values.append(volume_dict.get(str(current_date), 0))
            current_date += timedelta(days=1)
        
        return {
            'labels': labels,
            'values': values
        }
        
    except Exception as e:
        current_app.logger.error(f'获取交易量趋势失败: {str(e)}')
        return {'labels': [], 'values': []} 