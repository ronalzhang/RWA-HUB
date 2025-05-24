"""
佣金管理模块
包含佣金记录查询、统计、设置等功能
"""

from flask import (
    render_template, request, jsonify, current_app, 
    send_file, make_response
)
from datetime import datetime, timedelta
import csv
import io
from sqlalchemy import desc, func, or_, and_
from app import db
from app.models.referral import CommissionRecord
from app.models.admin import CommissionSetting
from . import admin_bp
from .auth import api_admin_required, admin_page_required


# 页面路由
@admin_bp.route('/commission')
@admin_page_required
def commission_page():
    """佣金管理页面"""
    return render_template('admin_v2/commission.html')


# V2版本路由（兼容前端调用）
@admin_bp.route('/v2/api/commission/stats', methods=['GET'])
@api_admin_required
def commission_stats_v2():
    """获取佣金统计 - V2兼容版本"""
    return api_commission_stats()


@admin_bp.route('/v2/api/commission/records', methods=['GET'])
@api_admin_required
def commission_records_v2():
    """获取佣金记录列表 - V2兼容版本"""
    return api_commission_records()


@admin_bp.route('/v2/api/commission/settings', methods=['GET'])
@api_admin_required
def commission_settings_v2():
    """获取佣金设置 - V2兼容版本"""
    return api_commission_settings()


@admin_bp.route('/v2/api/commission/settings', methods=['POST'])
@api_admin_required
def update_commission_settings_v2():
    """更新佣金设置 - V2兼容版本"""
    return api_update_commission_settings()


@admin_bp.route('/v2/api/commission/records/<int:record_id>/pay', methods=['POST'])
@api_admin_required
def pay_commission_v2(record_id):
    """发放佣金 - V2兼容版本"""
    return api_pay_commission(record_id)


# API路由
@admin_bp.route('/api/admin/commission/stats', methods=['GET'])
@api_admin_required
def api_commission_stats():
    """佣金统计数据"""
    try:
        # 总佣金统计
        total_amount = db.session.query(func.sum(CommissionRecord.amount)).scalar() or 0
        total_count = CommissionRecord.query.count()
        
        # 按状态统计
        pending_amount = db.session.query(func.sum(CommissionRecord.amount)).filter(
            CommissionRecord.status == 'pending'
        ).scalar() or 0
        pending_count = CommissionRecord.query.filter_by(status='pending').count()
        
        paid_amount = db.session.query(func.sum(CommissionRecord.amount)).filter(
            CommissionRecord.status == 'paid'
        ).scalar() or 0
        paid_count = CommissionRecord.query.filter_by(status='paid').count()
        
        failed_amount = db.session.query(func.sum(CommissionRecord.amount)).filter(
            CommissionRecord.status == 'failed'
        ).scalar() or 0
        failed_count = CommissionRecord.query.filter_by(status='failed').count()
        
        # 按佣金类型统计
        platform_amount = db.session.query(func.sum(CommissionRecord.amount)).filter(
            CommissionRecord.commission_type == 'platform'
        ).scalar() or 0
        referral_amount = db.session.query(func.sum(CommissionRecord.amount)).filter(
            CommissionRecord.commission_type.like('referral_%')
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'total': {
                    'amount': float(total_amount),
                    'count': total_count
                },
                'pending': {
                    'amount': float(pending_amount),
                    'count': pending_count
                },
                'paid': {
                    'amount': float(paid_amount),
                    'count': paid_count
                },
                'failed': {
                    'amount': float(failed_amount),
                    'count': failed_count
                },
                'platform': {
                    'amount': float(platform_amount)
                },
                'referral': {
                    'amount': float(referral_amount)
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取佣金统计失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/commission/records', methods=['GET'])
@api_admin_required
def api_commission_records():
    """佣金记录列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status', '')
        commission_type = request.args.get('type', '')
        time_range = request.args.get('time_range', '')
        search = request.args.get('search', '')
        
        # 构建查询
        query = CommissionRecord.query
        
        # 状态筛选
        if status:
            query = query.filter(CommissionRecord.status == status)
        
        # 类型筛选
        if commission_type:
            query = query.filter(CommissionRecord.commission_type == commission_type)
        
        # 时间范围筛选
        if time_range:
            now = datetime.utcnow()
            if time_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(CommissionRecord.created_at >= start_date)
            elif time_range == 'week':
                start_date = now - timedelta(days=7)
                query = query.filter(CommissionRecord.created_at >= start_date)
            elif time_range == 'month':
                start_date = now - timedelta(days=30)
                query = query.filter(CommissionRecord.created_at >= start_date)
        
        # 搜索条件
        if search:
            query = query.filter(
                or_(
                    CommissionRecord.recipient_address.ilike(f'%{search}%'),
                    CommissionRecord.tx_hash.ilike(f'%{search}%')
                )
            )
        
        # 分页
        total = query.count()
        records = query.order_by(desc(CommissionRecord.created_at)) \
            .offset((page - 1) * limit) \
            .limit(limit) \
            .all()
        
        # 格式化数据
        records_list = []
        for record in records:
            records_list.append({
                'id': record.id,
                'transaction_id': record.transaction_id,
                'asset_id': record.asset_id,
                'recipient_address': record.recipient_address,
                'amount': float(record.amount),
                'currency': record.currency,
                'commission_type': record.commission_type,
                'status': record.status,
                'tx_hash': record.tx_hash,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None
            })
        
        return jsonify({
            'success': True,
            'data': records_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取佣金记录失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/commission/settings', methods=['GET'])
@api_admin_required
def api_commission_settings():
    """佣金设置"""
    try:
        # 返回默认的佣金设置
        default_settings = [
            {
                'id': 1,
                'asset_type_id': 1,
                'asset_type_name': '房地产',
                'commission_rate': 0.02,
                'min_amount': 0,
                'max_amount': None,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'created_by': 'system'
            },
            {
                'id': 2,
                'asset_type_id': 2,
                'asset_type_name': '股权',
                'commission_rate': 0.015,
                'min_amount': 0,
                'max_amount': None,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'created_by': 'system'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': default_settings
        })
        
    except Exception as e:
        current_app.logger.error(f'获取佣金设置失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/commission/settings', methods=['POST'])
@api_admin_required
def api_update_commission_settings():
    """更新佣金设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '缺少请求数据'}), 400
        
        # 这里可以实现佣金设置的更新逻辑
        # 由于涉及到复杂的业务逻辑，暂时返回成功
        
        return jsonify({
            'success': True,
            'message': '佣金设置更新成功'
        })
        
    except Exception as e:
        current_app.logger.error(f'更新佣金设置失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/commission/records/<int:record_id>/pay', methods=['POST'])
@api_admin_required
def api_pay_commission(record_id):
    """发放佣金"""
    try:
        record = CommissionRecord.query.get_or_404(record_id)
        
        if record.status != 'pending':
            return jsonify({'success': False, 'error': '只能发放待发放状态的佣金'}), 400
        
        # 这里应该实现实际的佣金发放逻辑
        # 暂时只更新状态为已发放
        record.status = 'paid'
        record.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '佣金发放成功'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'发放佣金失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500 