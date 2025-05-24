"""
仪表板管理模块
"""

from flask import render_template, jsonify, current_app
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
    return render_template('admin/v2/dashboard.html')


@admin_bp.route('/')
@admin_page_required
def admin_index():
    """管理后台首页"""
    return render_template('admin/v2/dashboard.html')


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
        total_assets = Asset.query.filter(Asset.status != 0).count()
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