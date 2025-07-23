"""
安全的支付管理路由
管理员手动处理支付，不存储私钥
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
import json

from app.extensions import db
from .auth import api_admin_required, admin_page_required

# 创建蓝图
payment_management_bp = Blueprint('payment_management', __name__)

@payment_management_bp.route('/payment-management')
@admin_page_required
def payment_management():
    """支付管理页面"""
    return render_template('admin_v2/payment_management.html')

@payment_management_bp.route('/api/v2/pending-payments', methods=['GET'])
@api_admin_required
def get_pending_payments():
    """获取待处理支付列表"""
    try:
        # 临时返回空数据，等模型完善后再实现
        return jsonify({
            'success': True,
            'data': {
                'payments': [],
                'stats': {
                    'pending': 0,
                    'processing': 0,
                    'completed_today': 0,
                    'total_amount': 0,
                    'urgent': 0
                },
                'pagination': {
                    'page': 1,
                    'limit': 20,
                    'total': 0
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
@api_admin_required
def get_payment_stats_api():
    """获取支付统计数据"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'pending': 0,
                'processing': 0,
                'completed_today': 0,
                'total_amount': 0,
                'urgent': 0
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取支付统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取统计数据失败'
        }), 500

# 其他API路由暂时简化，等模型完善后再实现