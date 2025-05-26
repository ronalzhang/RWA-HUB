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
        # 导入User模型来统计推荐用户数
        from app.models.user import User
        
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
        
        # 统计推荐用户总数（有推荐人的用户数量）
        total_referrals = User.query.filter(User.referrer_address.isnot(None)).count()
        
        # 获取佣金率设置（从设置表获取，如果没有则使用默认值）
        commission_rate = 5.0  # 默认佣金率
        try:
            commission_setting = CommissionSetting.query.filter_by(key='global_rate').first()
            if commission_setting:
                commission_rate = float(commission_setting.value)
        except:
            pass
        
        # 返回前端期望的数据格式
        return jsonify({
            'success': True,
            'total_commission': float(total_amount),
            'total_referrals': total_referrals,
            'pending_commission': float(pending_amount),
            'commission_rate': commission_rate,
            # 保留详细数据供其他用途
            'details': {
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
        # 获取佣金设置，如果不存在则返回默认值
        settings = {}
        
        # 定义默认设置
        default_settings = {
            'global_rate': 5.0,
            'min_amount': 1.0,
            'referral_levels': 3,
            'level1_rate': 5.0,
            'level2_rate': 3.0,
            'level3_rate': 1.0
        }
        
        # 尝试从数据库获取设置
        try:
            for key, default_value in default_settings.items():
                setting = CommissionSetting.query.filter_by(key=key).first()
                if setting:
                    # 根据类型转换值
                    if key in ['referral_levels']:
                        settings[key] = int(setting.value)
                    else:
                        settings[key] = float(setting.value)
                else:
                    settings[key] = default_value
        except Exception as db_error:
            current_app.logger.warning(f'从数据库获取佣金设置失败，使用默认值: {str(db_error)}')
            settings = default_settings
        
        return jsonify({
            'success': True,
            **settings  # 直接返回设置字段，不嵌套在data中
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
        
        # 定义允许更新的设置字段
        allowed_settings = [
            'global_rate', 'min_amount', 'referral_levels',
            'level1_rate', 'level2_rate', 'level3_rate'
        ]
        
        # 验证和保存设置
        updated_count = 0
        for key in allowed_settings:
            if key in data:
                value = data[key]
                
                # 数据验证
                if key in ['global_rate', 'level1_rate', 'level2_rate', 'level3_rate']:
                    if not (0 <= float(value) <= 100):
                        return jsonify({'success': False, 'error': f'{key} 必须在0-100之间'}), 400
                elif key == 'min_amount':
                    if float(value) < 0:
                        return jsonify({'success': False, 'error': '最低佣金金额不能为负数'}), 400
                elif key == 'referral_levels':
                    if int(value) not in [1, 2, 3]:
                        return jsonify({'success': False, 'error': '推荐等级必须是1、2或3'}), 400
                
                # 查找或创建设置记录
                setting = CommissionSetting.query.filter_by(key=key).first()
                if setting:
                    setting.value = str(value)
                    setting.updated_at = datetime.utcnow()
                else:
                    setting = CommissionSetting(
                        key=key,
                        value=str(value),
                        description=f'佣金设置: {key}',
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(setting)
                
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            current_app.logger.info(f'佣金设置更新成功，更新了 {updated_count} 个设置项')
        
        return jsonify({
            'success': True,
            'message': f'佣金设置更新成功，更新了 {updated_count} 个设置项'
        })
        
    except Exception as e:
        db.session.rollback()
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


@admin_bp.route('/api/admin/commission/referrals', methods=['GET'])
@api_admin_required
def api_commission_referrals():
    """推荐关系列表"""
    try:
        from app.models.user import User
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        # 查询有推荐关系的用户
        query = User.query.filter(User.referrer_address.isnot(None))
        
        # 分页
        total = query.count()
        users = query.order_by(desc(User.created_at)) \
            .offset((page - 1) * limit) \
            .limit(limit) \
            .all()
        
        # 格式化数据
        referrals_list = []
        for user in users:
            referrals_list.append({
                'id': user.id,
                'user_address': user.eth_address or user.username,
                'referrer_address': user.referrer_address,
                'referral_level': 1,  # 默认一级推荐
                'referral_code': None,  # 暂时没有推荐码
                'joined_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return jsonify({
            'success': True,
            'items': referrals_list,
            'total': total,
            'pages': (total + limit - 1) // limit,
            'page': page,
            'limit': limit
        })
        
    except Exception as e:
        current_app.logger.error(f'获取推荐关系失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500 