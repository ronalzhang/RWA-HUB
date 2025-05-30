from flask import Blueprint, jsonify, request
from app.services.ip_stats_service import IPStatsService
from .auth import api_admin_required
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
ip_stats_bp = Blueprint('ip_stats', __name__, url_prefix='/admin/api/ip-stats')

@ip_stats_bp.route('/summary', methods=['GET'])
@api_admin_required
def get_summary_stats():
    """获取IP访问总体统计"""
    try:
        stats = IPStatsService.get_summary_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取IP统计总览失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ip_stats_bp.route('/hourly', methods=['GET'])
@api_admin_required
def get_hourly_stats():
    """获取24小时内每小时的访问统计"""
    try:
        # 可选参数：指定日期
        date_str = request.args.get('date')
        date = None
        if date_str:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        stats = IPStatsService.get_hourly_stats(date)
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取小时统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ip_stats_bp.route('/daily', methods=['GET'])
@api_admin_required
def get_daily_stats():
    """获取每日访问统计"""
    try:
        # 可选参数：天数
        days = request.args.get('days', 7, type=int)
        if days <= 0 or days > 365:
            days = 7
        
        stats = IPStatsService.get_daily_stats(days)
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取每日统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ip_stats_bp.route('/monthly', methods=['GET'])
@api_admin_required
def get_monthly_stats():
    """获取每月访问统计"""
    try:
        # 可选参数：月数
        months = request.args.get('months', 12, type=int)
        if months <= 0 or months > 60:
            months = 12
        
        stats = IPStatsService.get_monthly_stats(months)
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取每月统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ip_stats_bp.route('/all-time', methods=['GET'])
@api_admin_required
def get_all_time_stats():
    """获取全部时间访问统计"""
    try:
        stats = IPStatsService.get_all_time_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取全部时间统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ip_stats_bp.route('/top-ips', methods=['GET'])
@api_admin_required
def get_top_ips():
    """获取访问次数最多的IP地址"""
    try:
        from app.models import IPVisit
        from app.extensions import db
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # 可选参数：时间范围
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 查询访问次数最多的IP
        query = db.session.query(
            IPVisit.ip_address,
            func.count(IPVisit.id).label('visit_count'),
            func.max(IPVisit.timestamp).label('last_visit')
        ).filter(
            IPVisit.timestamp >= start_date
        ).group_by(
            IPVisit.ip_address
        ).order_by(
            func.count(IPVisit.id).desc()
        ).limit(limit)
        
        results = query.all()
        
        top_ips = []
        for r in results:
            top_ips.append({
                'ip_address': r.ip_address,
                'visit_count': r.visit_count,
                'last_visit': r.last_visit.isoformat() if r.last_visit else None
            })
        
        return jsonify({
            'success': True,
            'data': {
                'top_ips': top_ips,
                'period': f"最近{days}天",
                'total_count': len(top_ips)
            }
        })
    except Exception as e:
        logger.error(f"获取热门IP失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ip_stats_bp.route('/recent-visits', methods=['GET'])
@api_admin_required
def get_recent_visits():
    """获取最近的访问记录"""
    try:
        from app.models import IPVisit
        from app.extensions import db
        
        # 可选参数
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        
        # 分页查询最近访问记录
        pagination = IPVisit.query.order_by(
            IPVisit.timestamp.desc()
        ).paginate(
            page=page,
            per_page=limit,
            error_out=False
        )
        
        visits = []
        for visit in pagination.items:
            visits.append({
                'id': visit.id,
                'ip_address': visit.ip_address,
                'path': visit.path,
                'user_agent': visit.user_agent[:100] + '...' if visit.user_agent and len(visit.user_agent) > 100 else visit.user_agent,
                'referer': visit.referer,
                'timestamp': visit.timestamp.isoformat() if visit.timestamp else None
            })
        
        return jsonify({
            'success': True,
            'data': {
                'visits': visits,
                'pagination': {
                    'page': page,
                    'per_page': limit,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        })
    except Exception as e:
        logger.error(f"获取最近访问记录失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 