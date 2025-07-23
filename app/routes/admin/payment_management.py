"""
安全的支付管理路由
管理员手动处理支付，不存储私钥
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
import json

from app.models.pending_payment import PendingPayment, PaymentStatus, PaymentType, PaymentPriority
from app.models.admin import SystemConfig
from app.extensions import db
from app.utils.auth import admin_required

# 创建蓝图
payment_management_bp = Blueprint('payment_management', __name__)

@payment_management_bp.route('/payment-management')
@admin_required
def payment_management():
    """支付管理页面"""
    return render_template('admin_v2/payment_management.html')

@payment_management_bp.route('/api/v2/pending-payments', methods=['GET'])
@admin_required
def get_pending_payments():
    """获取待处理支付列表"""
    try:
        # 获取筛选参数
        status = request.args.get('status', '')
        payment_type = request.args.get('type', '')
        priority = request.args.get('priority', '')
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)  # 限制最大50条
        
        # 构建查询
        query = PendingPayment.query
        
        # 状态筛选
        if status:
            query = query.filter(PendingPayment.status == status)
        
        # 类型筛选
        if payment_type:
            query = query.filter(PendingPayment.payment_type == payment_type)
        
        # 优先级筛选
        if priority:
            query = query.filter(PendingPayment.priority == priority)
        
        # 排序：优先级高的在前，然后按创建时间排序
        query = query.order_by(
            PendingPayment.priority.desc(),
            PendingPayment.created_at.asc()
        )
        
        # 分页
        offset = (page - 1) * limit
        payments = query.offset(offset).limit(limit).all()
        
        # 获取统计数据
        stats = get_payment_stats()
        
        # 转换为字典格式
        payments_data = [payment.to_dict() for payment in payments]
        
        return jsonify({
            'success': True,
            'data': {
                'payments': payments_data,
                'stats': stats,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': query.count()
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取支付列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取支付列表失败'
        }), 500

@payment_management_bp.route('/api/v2/pending-payments/stats', methods=['GET'])
@admin_required
def get_payment_stats_api():
    """获取支付统计数据"""
    try:
        stats = get_payment_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        current_app.logger.error(f"获取支付统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取统计数据失败'
        }), 500

def get_payment_stats():
    """获取支付统计数据"""
    try:
        # 待处理数量
        pending_count = PendingPayment.query.filter_by(status=PaymentStatus.PENDING.value).count()
        
        # 处理中数量
        processing_count = PendingPayment.query.filter_by(status=PaymentStatus.PROCESSING.value).count()
        
        # 今日完成数量
        today = datetime.utcnow().date()
        completed_today = PendingPayment.query.filter(
            and_(
                PendingPayment.status == PaymentStatus.COMPLETED.value,
                func.date(PendingPayment.updated_at) == today
            )
        ).count()
        
        # 待处理总金额
        pending_amount_result = db.session.query(
            func.sum(PendingPayment.amount)
        ).filter_by(status=PaymentStatus.PENDING.value).scalar()
        
        total_amount = float(pending_amount_result or 0)
        
        # 紧急支付数量
        urgent_count = PendingPayment.query.filter(
            and_(
                PendingPayment.status == PaymentStatus.PENDING.value,
                PendingPayment.priority == PaymentPriority.URGENT.value
            )
        ).count()
        
        return {
            'pending': pending_count,
            'processing': processing_count,
            'completed_today': completed_today,
            'total_amount': total_amount,
            'urgent': urgent_count
        }
        
    except Exception as e:
        current_app.logger.error(f"获取统计数据失败: {str(e)}")
        return {
            'pending': 0,
            'processing': 0,
            'completed_today': 0,
            'total_amount': 0,
            'urgent': 0
        }

@payment_management_bp.route('/api/v2/pending-payments/<int:payment_id>/status', methods=['POST'])
@admin_required
def update_payment_status(payment_id):
    """更新支付状态"""
    try:
        data = request.get_json()
        status = data.get('status')
        tx_hash = data.get('tx_hash')
        error_message = data.get('error_message')
        processed_by = data.get('processed_by')  # 管理员钱包地址
        
        # 验证状态
        valid_statuses = [status.value for status in PaymentStatus]
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': '无效的状态'
            }), 400
        
        # 获取支付记录
        payment = PendingPayment.query.get(payment_id)
        if not payment:
            return jsonify({
                'success': False,
                'error': '找不到支付记录'
            }), 404
        
        # 更新状态
        payment.status = status
        payment.updated_at = datetime.utcnow()
        
        if status == PaymentStatus.PROCESSING.value:
            payment.processed_by = processed_by
            payment.processed_at = datetime.utcnow()
        elif status == PaymentStatus.COMPLETED.value:
            payment.tx_hash = tx_hash
            if not payment.processed_at:
                payment.processed_at = datetime.utcnow()
        elif status == PaymentStatus.FAILED.value:
            payment.failure_reason = error_message
            payment.retry_count += 1
        
        db.session.commit()
        
        current_app.logger.info(f"支付状态更新: ID={payment_id}, 状态={status}, 处理人={processed_by}")
        
        return jsonify({
            'success': True,
            'message': '状态更新成功',
            'data': payment.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新支付状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '更新状态失败'
        }), 500

@payment_management_bp.route('/api/v2/pending-payments/<int:payment_id>', methods=['GET'])
@admin_required
def get_payment_details(payment_id):
    """获取支付详情"""
    try:
        payment = PendingPayment.query.get(payment_id)
        if not payment:
            return jsonify({
                'success': False,
                'error': '找不到支付记录'
            }), 404
        
        return jsonify({
            'success': True,
            'data': payment.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"获取支付详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取支付详情失败'
        }), 500

@payment_management_bp.route('/api/v2/pending-payments/batch-process', methods=['POST'])
@admin_required
def batch_process_payments():
    """批量处理支付"""
    try:
        data = request.get_json()
        payment_ids = data.get('payment_ids', [])
        processed_by = data.get('processed_by')  # 管理员钱包地址
        
        if not payment_ids:
            return jsonify({
                'success': False,
                'error': '请选择要处理的支付'
            }), 400
        
        # 验证支付记录
        payments = PendingPayment.query.filter(
            and_(
                PendingPayment.id.in_(payment_ids),
                PendingPayment.status == PaymentStatus.PENDING.value
            )
        ).all()
        
        if len(payments) != len(payment_ids):
            return jsonify({
                'success': False,
                'error': '部分支付记录不存在或状态不正确'
            }), 400
        
        # 批量更新为处理中状态
        for payment in payments:
            payment.status = PaymentStatus.PROCESSING.value
            payment.processed_by = processed_by
            payment.processed_at = datetime.utcnow()
            payment.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # 构建批量交易数据
        batch_data = {
            'payments': [payment.to_dict() for payment in payments],
            'total_amount': sum(float(payment.amount) for payment in payments),
            'count': len(payments)
        }
        
        current_app.logger.info(f"批量处理支付: {len(payments)}个支付项，处理人={processed_by}")
        
        return jsonify({
            'success': True,
            'message': f'已标记{len(payments)}个支付为处理中',
            'data': batch_data
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量处理支付失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '批量处理失败'
        }), 500

@payment_management_bp.route('/api/v2/pending-payments/create-withdrawal', methods=['POST'])
@admin_required
def create_withdrawal_request():
    """创建提现请求（测试用）"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = float(data.get('amount'))
        recipient_address = data.get('recipient_address')
        token_symbol = data.get('token_symbol', 'USDC')
        
        # 创建提现请求
        payment = PendingPayment.create_withdrawal_request(
            user_id=user_id,
            amount=amount,
            recipient_address=recipient_address,
            token_symbol=token_symbol
        )
        
        return jsonify({
            'success': True,
            'message': '提现请求创建成功',
            'data': payment.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"创建提现请求失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '创建提现请求失败'
        }), 500

@payment_management_bp.route('/api/v2/pending-payments/authorized-addresses', methods=['GET'])
@admin_required
def get_authorized_addresses():
    """获取授权的管理员地址列表"""
    try:
        # 从系统配置获取授权地址
        authorized_addresses = []
        
        # 平台费用地址（通常是主管理员地址）
        platform_address = SystemConfig.get_value('PLATFORM_FEE_ADDRESS')
        if platform_address:
            authorized_addresses.append(platform_address)
        
        # 可以添加其他授权地址
        additional_addresses = SystemConfig.get_value('AUTHORIZED_PAYMENT_ADDRESSES')
        if additional_addresses:
            try:
                additional_list = json.loads(additional_addresses)
                authorized_addresses.extend(additional_list)
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': {
                'addresses': authorized_addresses
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取授权地址失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取授权地址失败'
        }), 500

# 注册蓝图
def register_payment_management_routes(app):
    """注册支付管理路由"""
    app.register_blueprint(payment_management_bp, url_prefix='/admin')