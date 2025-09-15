"""
佣金管理模块
包含佣金记录查询、统计、设置、取现记录等功能
"""

from flask import (
    render_template, request, jsonify, current_app, 
    send_file, make_response
)
from datetime import datetime, timedelta
import csv
import io
import json
from sqlalchemy import desc, func, or_, and_
from app import db
from app.models.referral import CommissionRecord
from app.models.admin import CommissionSetting
from app.models.commission_withdrawal import CommissionWithdrawal
from app.models.commission_config import UserCommissionBalance
from . import admin_bp
from . import admin_api_bp
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


@admin_bp.route('/v2/api/commission/withdrawals', methods=['GET'])
@api_admin_required
def commission_withdrawals_v2():
    """获取取现记录列表 - V2兼容版本"""
    return api_commission_withdrawals()


@admin_bp.route('/v2/api/commission/referrals', methods=['GET'])
@api_admin_required
def commission_referrals_v2():
    """获取推荐关系列表 - V2兼容版本"""
    return api_commission_referrals()


@admin_bp.route('/v2/api/commission/withdrawals/<int:withdrawal_id>/process', methods=['POST'])
@api_admin_required
def process_withdrawal_v2(withdrawal_id):
    """处理提现申请 - V2兼容版本"""
    return api_process_withdrawal(withdrawal_id)


@admin_bp.route('/v2/api/commission/withdrawals/<int:withdrawal_id>/cancel', methods=['POST'])
@api_admin_required
def cancel_withdrawal_v2(withdrawal_id):
    """取消提现申请 - V2兼容版本"""
    return api_cancel_withdrawal(withdrawal_id)


@admin_bp.route('/v2/api/commission/records/<int:record_id>/pay', methods=['POST'])
@api_admin_required
def pay_commission_v2(record_id):
    """发放佣金 - V2兼容版本"""
    return api_pay_commission(record_id)


@admin_bp.route('/v2/api/commission/records/export', methods=['GET'])
@api_admin_required
def export_records_v2():
    """导出佣金记录 - V2兼容版本"""
    return api_export_commission_records()


# API路由 - 使用admin_api_bp蓝图（前缀：/api/admin）
@admin_api_bp.route('/commission/stats', methods=['GET'])
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
        
        # 获取佣金率设置（从配置表获取，如果没有则使用默认值）
        from app.models.commission_config import CommissionConfig
        commission_rate = CommissionConfig.get_config('commission_rate', 35.0)
        
        # 获取提现统计
        withdrawal_stats = CommissionWithdrawal.get_withdrawal_stats()
        
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
            },
            # 添加提现统计
            'withdrawals': withdrawal_stats
        })
        
    except Exception as e:
        current_app.logger.error(f'获取佣金统计失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/records', methods=['GET'])
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


@admin_api_bp.route('/commission/settings', methods=['GET', 'POST'])
@api_admin_required
def api_commission_settings():
    """佣金设置管理"""
    if request.method == 'GET':
        try:
            from app.models.commission_config import CommissionConfig
            
            settings = {}
            # 获取所有配置（设置默认值）
            # 从配置管理器获取平台收款地址
            from app.utils.config_manager import ConfigManager
            platform_fee_address = ConfigManager.get_config('PLATFORM_FEE_ADDRESS')

            config_defaults = {
                'commission_rate': 35.0,
                'commission_description': '推荐好友享受35%佣金奖励',
                'share_button_text': '分享赚佣金',
                'share_description': '分享此项目给好友，好友购买后您将获得35%佣金奖励',
                'share_success_message': '分享链接已复制，快去邀请好友吧！',
                'min_withdraw_amount': 10.0,
                'withdraw_fee_rate': 0.0,
                'withdraw_description': '最低提现金额10 USDC，提现将转入您的钱包地址',
                'withdrawal_delay_minutes': 1,
                'max_referral_levels': 999,
                'enable_multi_level': True,
                'platform_referrer_address': platform_fee_address,  # 使用平台收款地址
                'enable_platform_referrer': True
            }

            for key, default_value in config_defaults.items():
                settings[key] = CommissionConfig.get_config(key, default_value)
            
            # 获取佣金计算规则
            commission_rules = CommissionConfig.get_config('commission_rules', {})
            if isinstance(commission_rules, str):
                import json
                try:
                    commission_rules = json.loads(commission_rules)
                except:
                    commission_rules = {}
            settings['commission_rules'] = commission_rules
            
            return jsonify({'success': True, 'data': settings})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    else:  # POST
        try:
            from app.models.commission_config import CommissionConfig
            from app.extensions import db
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': '无效的请求数据'})
            
            # 🔍 检测平台推荐人地址是否变更
            old_platform_address = CommissionConfig.get_config('platform_referrer_address', '')
            new_platform_address = data.get('platform_referrer_address', '').strip()
            address_changed = False
            
            if (old_platform_address and new_platform_address and 
                old_platform_address != new_platform_address):
                address_changed = True
                
                # 获取使用旧地址的用户数量
                from app.models.user import User
                old_address_users_count = User.query.filter_by(
                    referrer_address=old_platform_address, 
                    is_active=True
                ).count()
            
            # 保存所有配置
            for key, value in data.items():
                if key == 'commission_rules' and isinstance(value, dict):
                    import json
                    CommissionConfig.set_config(key, json.dumps(value))
                else:
                    CommissionConfig.set_config(key, value)
            
            db.session.commit()
            
            # 🎯 自动处理平台推荐人逻辑（新用户自动设置）
            response_data = {
                'success': True,
                'message': '佣金设置保存成功'
            }
            
            # 如果平台地址发生变更，返回变更信息
            if address_changed:
                response_data.update({
                    'address_changed': True,
                    'old_address': old_platform_address,
                    'new_address': new_platform_address,
                    'old_address_users_count': old_address_users_count,
                    'message': f'佣金设置保存成功！检测到平台推荐人地址已更换，有 {old_address_users_count} 个用户仍使用旧地址。'
                })
            
            # 特殊处理：如果设置了平台推荐人地址且启用了功能，自动将现有无推荐人的用户设置为平台的下线
            if ('platform_referrer_address' in data and data['platform_referrer_address'] and 
                data.get('enable_platform_referrer', True)):
                
                platform_address = data['platform_referrer_address'].strip()
                if platform_address:
                    try:
                        from app.models.user import User
                        from app.extensions import db
                        
                        # 查找所有没有推荐人的活跃用户
                        all_users_without_referrer = User.query.filter(
                            User.referrer_address.is_(None),
                            User.is_active == True
                        ).all()
                        
                        # 过滤掉平台地址本身（避免自己推荐自己）
                        users_to_update = []
                        for user in all_users_without_referrer:
                            # 检查用户不是平台地址本身
                            if (user.eth_address != platform_address and 
                                user.solana_address != platform_address):
                                users_to_update.append(user)
                        
                        # 批量更新推荐人
                        if users_to_update:
                            for user in users_to_update:
                                user.referrer_address = platform_address
                            
                            db.session.commit()
                            
                            response_data['auto_assigned_count'] = len(users_to_update)
                            if 'message' in response_data:
                                response_data['message'] += f' 同时自动将 {len(users_to_update)} 个无推荐人用户设置为平台下线。'
                        
                    except Exception as e:
                        current_app.logger.error(f"自动设置平台推荐人失败: {e}")
                        # 不影响主要的设置保存流程
            
            return jsonify(response_data)
            
        except Exception as e:
            current_app.logger.error(f"保存佣金设置失败: {e}")
            return jsonify({'success': False, 'error': str(e)})


@admin_api_bp.route('/commission/withdrawals', methods=['GET'])
@api_admin_required
def api_commission_withdrawals():
    """取现记录列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        
        # 构建查询
        query = CommissionWithdrawal.query
        
        # 状态筛选
        if status:
            query = query.filter(CommissionWithdrawal.status == status)
        
        # 搜索条件
        if search:
            query = query.filter(
                or_(
                    CommissionWithdrawal.user_address.ilike(f'%{search}%'),
                    CommissionWithdrawal.to_address.ilike(f'%{search}%'),
                    CommissionWithdrawal.tx_hash.ilike(f'%{search}%')
                )
            )
        
        # 分页
        total = query.count()
        withdrawals = query.order_by(desc(CommissionWithdrawal.created_at)) \
            .offset((page - 1) * limit) \
            .limit(limit) \
            .all()
        
        # 格式化数据
        withdrawals_list = []
        for withdrawal in withdrawals:
            data = withdrawal.to_dict()
            # 添加剩余延迟时间
            data['remaining_delay_seconds'] = withdrawal.remaining_delay_seconds
            data['is_ready_to_process'] = withdrawal.is_ready_to_process
            withdrawals_list.append(data)
        
        return jsonify({
            'success': True,
            'data': withdrawals_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取取现记录失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/withdrawals/<int:withdrawal_id>/process', methods=['POST'])
@api_admin_required
def api_process_withdrawal(withdrawal_id):
    """处理提现申请 - 现在为自动化系统，仅作为手动触发器"""
    try:
        from app.services.auto_commission_service import AutoCommissionService
        
        withdrawal = CommissionWithdrawal.query.get_or_404(withdrawal_id)
        
        if withdrawal.status != 'pending':
            return jsonify({'success': False, 'error': '只能处理待处理状态的提现申请'}), 400
        
        # 使用自动化服务处理
        success = AutoCommissionService._process_single_withdrawal(withdrawal)
        
        if success:
            return jsonify({
                'success': True,
                'message': '提现处理成功（自动化处理）',
                'tx_hash': withdrawal.tx_hash
            })
        else:
            return jsonify({
                'success': False,
                'error': '自动化处理失败，请查看取现记录状态'
            })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'处理提现失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/withdrawals/<int:withdrawal_id>/cancel', methods=['POST'])
@api_admin_required
def api_cancel_withdrawal(withdrawal_id):
    """取消提现申请 - 仍保留管理员取消功能"""
    try:
        from app.models.commission_config import UserCommissionBalance
        
        data = request.get_json() or {}
        reason = data.get('reason', '管理员取消')
        
        withdrawal = CommissionWithdrawal.query.get_or_404(withdrawal_id)
        
        if withdrawal.status not in ['pending', 'processing']:
            return jsonify({'success': False, 'error': '只能取消待处理或处理中的提现申请'}), 400
        
        # 如果是取消，需要退还余额
        if withdrawal.status == 'pending':
            user_balance = UserCommissionBalance.query.filter_by(
                user_address=withdrawal.user_address
            ).first()
            
            if user_balance and user_balance.frozen_balance >= withdrawal.amount:
                # 从冻结余额退还到可用余额
                user_balance.frozen_balance -= withdrawal.amount
                user_balance.available_balance += withdrawal.amount
                db.session.commit()
        
        withdrawal.cancel(reason)
        
        return jsonify({
            'success': True,
            'message': '提现申请已取消，金额已退还到用户余额'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'取消提现失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/automation/run', methods=['POST'])
@api_admin_required
def api_run_automation():
    """手动运行自动化周期"""
    try:
        from app.services.auto_commission_service import AutoCommissionService
        
        result = AutoCommissionService.run_automation_cycle()
        
        return jsonify({
            'success': True,
            'message': '自动化周期执行完成',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f'运行自动化周期失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/automation/status', methods=['GET'])
@api_admin_required
def api_automation_status():
    """获取自动化系统状态"""
    try:
        from app.services.auto_commission_service import AutoCommissionService
        from app.models.commission_config import CommissionConfig
        
        # 获取待处理的取现数量
        pending_withdrawals = CommissionWithdrawal.get_pending_withdrawals()
        ready_to_process = CommissionWithdrawal.get_ready_to_process()
        
        # 获取自动化配置
        automation_config = {
            'withdrawal_delay_minutes': CommissionConfig.get_config('withdrawal_delay_minutes', 1),
            'min_withdraw_amount': CommissionConfig.get_config('min_withdraw_amount', 10.0),
            'commission_rate': CommissionConfig.get_config('commission_rate', 35.0),
            'max_referral_levels': CommissionConfig.get_config('max_referral_levels', 999),
            'enable_multi_level': CommissionConfig.get_config('enable_multi_level', True)
        }
        
        return jsonify({
            'success': True,
            'data': {
                'automation_enabled': True,
                'pending_withdrawals_count': len(pending_withdrawals),
                'ready_to_process_count': len(ready_to_process),
                'automation_config': automation_config,
                'system_status': 'active'
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取自动化状态失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/user/<string:user_address>/summary', methods=['GET'])
@api_admin_required
def api_user_commission_summary(user_address):
    """获取用户佣金详细摘要"""
    try:
        from app.services.auto_commission_service import AutoCommissionService
        
        summary = AutoCommissionService.get_commission_summary(user_address)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        current_app.logger.error(f'获取用户佣金摘要失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/create_withdrawal', methods=['POST'])
@api_admin_required  
def api_create_withdrawal():
    """管理员代用户创建取现申请"""
    try:
        from app.services.auto_commission_service import AutoCommissionService
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '缺少请求数据'}), 400
        
        user_address = data.get('user_address')
        to_address = data.get('to_address')
        amount = data.get('amount')
        currency = data.get('currency', 'USDC')
        
        if not all([user_address, to_address, amount]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': '金额格式错误'}), 400
        
        result = AutoCommissionService.create_auto_withdrawal(
            user_address, to_address, amount, currency
        )
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f'创建取现申请失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/referrals', methods=['GET'])
@api_admin_required
def api_commission_referrals():
    """推荐关系列表 - 显示所有用户的推荐关系信息"""
    try:
        from app.models.user import User
        from app.models.commission_config import CommissionConfig
        from sqlalchemy import func
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)  # 增加每页显示数量
        search = request.args.get('search', '')
        
        # 查询所有用户（不只是有推荐关系的）
        query = User.query.filter(User.is_active == True)
        
        # 搜索条件
        if search:
            query = query.filter(
                or_(
                    User.username.ilike(f'%{search}%'),
                    User.eth_address.ilike(f'%{search}%'),
                    User.solana_address.ilike(f'%{search}%'),
                    User.referrer_address.ilike(f'%{search}%')
                )
            )
        
        # 分页
        total = query.count()
        users = query.order_by(desc(User.created_at)) \
            .offset((page - 1) * limit) \
            .limit(limit) \
            .all()
        
        # 获取平台推荐人地址
        platform_referrer_address = CommissionConfig.get_config('platform_referrer_address', '')
        
        # 格式化数据
        referrals_list = []
        for user in users:
            # 获取主要钱包地址
            main_address = user.eth_address or user.solana_address or f"user_{user.id}"
            
            # 统计下级用户数量
            downline_count = User.query.filter_by(referrer_address=main_address).count()
            
            # 判断推荐人类型
            referrer_type = 'normal'
            if user.referrer_address == platform_referrer_address:
                referrer_type = 'platform'
            elif not user.referrer_address:
                referrer_type = 'none'
            
            # 计算推荐层级（简化版本，这里只显示直接推荐）
            referral_level = 1 if user.referrer_address else 0
            
            # 钱包类型
            wallet_type = 'ethereum' if user.eth_address else ('solana' if user.solana_address else 'other')
            
            referrals_list.append({
                'id': user.id,
                'username': user.username,
                'user_address': main_address,
                'eth_address': user.eth_address,
                'solana_address': user.solana_address,
                'wallet_type': wallet_type,
                'referrer_address': user.referrer_address,
                'referrer_type': referrer_type,
                'downline_count': downline_count,
                'referral_level': referral_level,
                'is_active': user.is_active,
                'joined_at': user.created_at.isoformat() if user.created_at else None,
                'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None
            })
        
        # 统计总体数据
        total_users = User.query.filter(User.is_active == True).count()
        users_with_referrer = User.query.filter(User.referrer_address.isnot(None)).count()
        platform_users = User.query.filter_by(referrer_address=platform_referrer_address).count() if platform_referrer_address else 0
        orphan_users = User.query.filter(User.referrer_address.is_(None)).count()
        
        return jsonify({
            'success': True,
            'items': referrals_list,
            'total': total,
            'pages': (total + limit - 1) // limit,
            'page': page,
            'limit': limit,
            'statistics': {
                'total_users': total_users,
                'users_with_referrer': users_with_referrer,
                'platform_users': platform_users,
                'orphan_users': orphan_users
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取推荐关系失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/records/<int:record_id>/pay', methods=['POST'])
@api_admin_required
def api_pay_commission(record_id):
    """发放佣金"""
    try:
        record = CommissionRecord.query.get_or_404(record_id)
        
        if record.status != 'pending':
            return jsonify({'success': False, 'error': '只能发放待处理状态的佣金'}), 400
        
        # 标记为已发放
        record.status = 'paid'
        record.payment_time = datetime.utcnow()
        
        # TODO: 这里应该实现实际的区块链转账逻辑
        # 暂时模拟发放成功
        import uuid
        record.tx_hash = f"0x{uuid.uuid4().hex}"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '佣金发放成功',
            'tx_hash': record.tx_hash
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'发放佣金失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/records/export', methods=['GET'])
@api_admin_required
def api_export_commission_records():
    """导出佣金记录"""
    try:
        import csv
        import io
        from flask import make_response
        
        # 获取所有佣金记录
        records = CommissionRecord.query.order_by(desc(CommissionRecord.created_at)).all()
        
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            'ID', '交易ID', '资产ID', '接收地址', '金额', '币种', 
            '佣金类型', '状态', '交易哈希', '创建时间', '更新时间'
        ])
        
        # 写入数据
        for record in records:
            writer.writerow([
                record.id,
                record.transaction_id,
                record.asset_id,
                record.recipient_address,
                record.amount,
                record.currency,
                record.commission_type,
                record.status,
                record.tx_hash or '',
                record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else '',
                record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if record.updated_at else ''
            ])
        
        # 创建响应
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=commission_records_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f'导出佣金记录失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/platform-referrer/batch-update', methods=['POST'])
@api_admin_required
def api_batch_update_platform_referrer():
    """手动批量更新平台推荐人关系"""
    try:
        from app.models.commission_config import CommissionConfig
        from app.models.user import User
        from app.extensions import db
        
        # 获取平台推荐人地址
        platform_address = CommissionConfig.get_config('platform_referrer_address', '')
        enable_platform_referrer = CommissionConfig.get_config('enable_platform_referrer', True)
        
        if not platform_address or not enable_platform_referrer:
            return jsonify({
                'success': False, 
                'error': '请先在佣金设置中配置并启用平台推荐人功能'
            }), 400
        
        # 查找所有没有推荐人的活跃用户
        all_users_without_referrer = User.query.filter(
            User.referrer_address.is_(None),
            User.is_active == True
        ).all()
        
        # 过滤掉平台地址本身（避免自己推荐自己）
        users_to_update = []
        for user in all_users_without_referrer:
            # 检查是否是平台地址本身
            if (user.eth_address != platform_address and 
                user.solana_address != platform_address):
                users_to_update.append(user)
        
        updated_count = 0
        user_details = []
        
        for user in users_to_update:
            user.referrer_address = platform_address
            updated_count += 1
            
            user_details.append({
                'id': user.id,
                'username': user.username,
                'eth_address': user.eth_address,
                'solana_address': user.solana_address,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        db.session.commit()
        
        current_app.logger.info(f"手动批量更新：已将 {updated_count} 个无推荐人用户设置为平台下线")
        
        return jsonify({
            'success': True,
            'message': f'批量更新成功！已将 {updated_count} 个无推荐人用户设置为平台下线',
            'data': {
                'updated_count': updated_count,
                'platform_address': platform_address,
                'user_details': user_details[:10]  # 只返回前10个用户详情避免数据过大
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量更新平台推荐人关系失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# 以下API用于前端调用（非管理员权限）
@admin_api_bp.route('/commission/share-config', methods=['GET'])
def get_share_config():
    """获取分享配置（前端调用）"""
    try:
        from app.models.commission_config import CommissionConfig

        config = {
            'share_button_text': CommissionConfig.get_config('share_button_text', '分享赚佣金'),
            'share_description': CommissionConfig.get_config('share_description', '分享此项目给好友，好友购买后您将获得35%佣金奖励'),
            'share_success_message': CommissionConfig.get_config('share_success_message', '分享链接已复制，快去邀请好友吧！'),
            'commission_rate': CommissionConfig.get_config('commission_rate', 35.0),
            'commission_description': CommissionConfig.get_config('commission_description', '推荐好友享受35%佣金奖励')
        }

        return jsonify({
            'success': True,
            'data': config
        })

    except Exception as e:
        current_app.logger.error(f"获取分享配置失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_api_bp.route('/user/commission/balance/<address>', methods=['GET'])
def get_user_commission_balance(address):
    """获取用户佣金余额（钱包显示）"""
    try:
        from app.models.commission_config import UserCommissionBalance

        balance = UserCommissionBalance.get_balance(address)

        return jsonify({
            'success': True,
            'data': balance.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"获取用户佣金余额失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_api_bp.route('/user/commission/withdraw', methods=['POST'])
def withdraw_commission():
    """提现佣金"""
    try:
        from app.models.commission_config import UserCommissionBalance, CommissionConfig
        from app.models.commission_withdrawal import CommissionWithdrawal

        data = request.get_json()
        user_address = data.get('user_address')
        amount = float(data.get('amount', 0))
        to_address = data.get('to_address')  # 提现到的钱包地址
        note = data.get('note', '')  # 用户备注

        if not user_address or not to_address or amount <= 0:
            return jsonify({'error': '参数错误'}), 400

        # 检查最低提现金额
        min_withdraw = CommissionConfig.get_config('min_withdraw_amount', 10.0)
        if amount < min_withdraw:
            return jsonify({'error': f'最低提现金额为 {min_withdraw} USDC'}), 400

        # 获取提现延迟设置
        withdraw_delay = CommissionConfig.get_config('withdraw_delay_minutes', 1)

        # 检查用户余额
        balance = UserCommissionBalance.get_balance(user_address)
        if balance.available_balance < amount:
            return jsonify({'error': '余额不足'}), 400

        # 冻结提现金额
        UserCommissionBalance.update_balance(user_address, amount, 'freeze')

        # 创建提现记录
        withdrawal = CommissionWithdrawal(
            user_address=user_address,
            to_address=to_address,
            amount=amount,
            delay_minutes=withdraw_delay,
            note=note
        )
        db.session.add(withdrawal)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'提现申请已提交，预计 {withdraw_delay} 分钟后处理',
            'data': {
                'withdrawal_id': withdrawal.id,
                'amount': float(withdrawal.amount),
                'to_address': withdrawal.to_address,
                'delay_minutes': withdrawal.delay_minutes,
                'process_at': withdrawal.process_at.isoformat() if withdrawal.process_at else None,
                'remaining_seconds': withdrawal.remaining_delay_seconds
            }
        })

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"提现失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_api_bp.route('/commission/user/<int:user_id>/set-platform-referrer', methods=['POST'])
@api_admin_required
def api_set_user_platform_referrer(user_id):
    """设置单个用户为平台下线"""
    try:
        from app.models.commission_config import CommissionConfig
        from app.models.user import User
        from app.extensions import db
        
        # 获取平台推荐人地址
        platform_address = CommissionConfig.get_config('platform_referrer_address', '')
        enable_platform_referrer = CommissionConfig.get_config('enable_platform_referrer', True)
        
        if not platform_address or not enable_platform_referrer:
            return jsonify({
                'success': False, 
                'error': '请先在佣金设置中配置并启用平台推荐人功能'
            }), 400
        
        # 查找指定用户
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False, 
                'error': f'未找到ID为 {user_id} 的用户'
            }), 404
        
        # 检查用户是否已有推荐人
        if user.referrer_address:
            return jsonify({
                'success': False, 
                'error': f'用户 {user.username} 已有推荐人: {user.referrer_address}'
            }), 400
        
        # 检查用户地址是否就是平台地址（避免自己推荐自己）
        if user.eth_address == platform_address or user.solana_address == platform_address:
            return jsonify({
                'success': False, 
                'error': '不能将平台地址设置为自己的下线'
            }), 400
        
        # 设置推荐人
        old_referrer = user.referrer_address
        user.referrer_address = platform_address
        
        db.session.commit()
        
        current_app.logger.info(f"手动设置用户 {user.username} (ID: {user.id}) 为平台下线，推荐人从 {old_referrer} 更新为 {platform_address}")
        
        return jsonify({
            'success': True,
            'message': f'成功将用户 {user.username} 设置为平台下线',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'old_referrer': old_referrer,
                'new_referrer': platform_address,
                'platform_address': platform_address
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'设置用户平台推荐人关系失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/commission/platform-referrer/migrate-old-address', methods=['POST'])
@api_admin_required
def api_migrate_old_platform_address():
    """批量更新旧平台推荐人地址到新地址"""
    try:
        from app.models.commission_config import CommissionConfig
        from app.models.user import User
        from app.extensions import db
        import json
        from datetime import datetime
        
        data = request.get_json() or {}
        old_address = data.get('old_address', '').strip()
        new_address = data.get('new_address', '').strip()
        
        if not old_address or not new_address:
            return jsonify({
                'success': False, 
                'error': '请提供有效的旧地址和新地址'
            }), 400
            
        if old_address == new_address:
            return jsonify({
                'success': False, 
                'error': '新旧地址不能相同'
            }), 400
        
        # 获取当前平台推荐人地址确认
        current_platform_address = CommissionConfig.get_config('platform_referrer_address', '')
        if new_address != current_platform_address:
            return jsonify({
                'success': False, 
                'error': '新地址必须与当前配置的平台推荐人地址一致'
            }), 400
        
        # 查找所有使用旧平台地址的用户
        users_with_old_address = User.query.filter(
            User.referrer_address == old_address,
            User.is_active == True
        ).all()
        
        if not users_with_old_address:
            return jsonify({
                'success': False, 
                'error': f'没有找到使用地址 {old_address[:10]}... 的用户'
            }), 404
        
        # 执行批量更新
        updated_count = 0
        for user in users_with_old_address:
            user.referrer_address = new_address
            updated_count += 1
        
        # 记录操作日志
        operation_log = {
            'operation': 'migrate_platform_address',
            'old_address': old_address,
            'new_address': new_address,
            'updated_users_count': updated_count,
            'updated_user_ids': [user.id for user in users_with_old_address],
            'timestamp': datetime.now().isoformat(),
            'admin_user': 'admin'  # 可以从session获取管理员信息
        }
        
        # 保存操作日志到配置中
        existing_logs = CommissionConfig.get_config('platform_address_migration_logs', '[]')
        try:
            logs = json.loads(existing_logs) if existing_logs else []
        except:
            logs = []
        
        logs.append(operation_log)
        # 只保留最近10条记录
        if len(logs) > 10:
            logs = logs[-10:]
        
        CommissionConfig.set_config('platform_address_migration_logs', json.dumps(logs))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功将 {updated_count} 个用户的推荐人地址从旧地址更新为新地址',
            'data': {
                'old_address': old_address,
                'new_address': new_address,
                'updated_count': updated_count,
                'updated_users': [
                    {
                        'id': user.id,
                        'username': user.username,
                        'eth_address': user.eth_address,
                        'solana_address': user.solana_address
                    } for user in users_with_old_address
                ],
                'operation_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"批量更新平台地址失败: {e}")
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': f'批量更新失败: {str(e)}'
        }), 500


@admin_api_bp.route('/commission/platform-referrer/old-addresses', methods=['GET'])
@api_admin_required
def api_get_old_platform_addresses():
    """获取所有历史平台推荐人地址的用户分布"""
    try:
        from app.models.commission_config import CommissionConfig
        from app.models.user import User
        from sqlalchemy import func
        
        # 获取当前平台地址
        current_platform_address = CommissionConfig.get_config('platform_referrer_address', '')
        
        # 查询所有作为推荐人的地址及其用户数量
        referrer_stats = db.session.query(
            User.referrer_address,
            func.count(User.id).label('user_count')
        ).filter(
            User.referrer_address.isnot(None),
            User.is_active == True
        ).group_by(User.referrer_address).all()
        
        # 区分平台地址和普通推荐人地址
        platform_addresses = []
        normal_referrers = []
        
        for referrer_address, user_count in referrer_stats:
            address_info = {
                'address': referrer_address,
                'user_count': user_count,
                'is_current': referrer_address == current_platform_address
            }
            
            # 判断是否为平台地址（简单判断：地址长度和格式特征）
            if (len(referrer_address) > 30 and 
                (referrer_address.startswith('0x') or len(referrer_address) > 40)):
                # 进一步检查是否在用户表中作为普通用户存在
                user_exists = User.query.filter(
                    db.or_(
                        User.eth_address == referrer_address,
                        User.solana_address == referrer_address
                    )
                ).first()
                
                if user_exists:
                    normal_referrers.append({
                        **address_info,
                        'username': user_exists.username
                    })
                else:
                    platform_addresses.append(address_info)
            else:
                normal_referrers.append(address_info)
        
        # 获取操作日志
        logs_json = CommissionConfig.get_config('platform_address_migration_logs', '[]')
        try:
            migration_logs = json.loads(logs_json) if logs_json else []
        except:
            migration_logs = []
        
        return jsonify({
            'success': True,
            'data': {
                'current_platform_address': current_platform_address,
                'platform_addresses': platform_addresses,
                'normal_referrers': normal_referrers,
                'migration_logs': migration_logs[-5:],  # 只返回最近5条
                'total_platform_users': sum(addr['user_count'] for addr in platform_addresses)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取历史平台地址失败: {e}")
        return jsonify({
            'success': False, 
            'error': f'获取数据失败: {str(e)}'
        }), 500 