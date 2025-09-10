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

@payment_management_bp.route('/api/v2/payment-config', methods=['GET'])
@api_admin_required
def get_payment_config():
    """获取支付配置"""
    try:
        from app.models.admin import SystemConfig
        
        # 获取所有支付相关配置
        config_keys = [
            'PLATFORM_COMMISSION_RATE',
            'PLATFORM_FEE_ADDRESS',
            'ASSET_CREATION_FEE_AMOUNT',
            'ASSET_CREATION_FEE_ADDRESS'
        ]
        
        config_data = {}
        for key in config_keys:
            value = SystemConfig.get_value(key)
            if key == 'PLATFORM_COMMISSION_RATE':
                config_data['platform_commission_rate'] = float(value) if value else 0.20
            elif key == 'PLATFORM_FEE_ADDRESS':
                config_data['platform_fee_address'] = value or ''
            elif key == 'ASSET_CREATION_FEE_AMOUNT':
                config_data['asset_creation_fee_amount'] = float(value) if value else 0.02
            elif key == 'ASSET_CREATION_FEE_ADDRESS':
                config_data['asset_creation_fee_address'] = value or ''
        
        return jsonify({
            'success': True,
            'data': config_data
        })
        
    except Exception as e:
        current_app.logger.error(f"获取支付配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取支付配置失败'
        }), 500

@payment_management_bp.route('/api/v2/payment-config', methods=['POST'])
@api_admin_required
def update_payment_config():
    """更新支付配置"""
    try:
        from app.models.admin import SystemConfig
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        # 配置映射
        config_mapping = {
            'platform_commission_rate': 'PLATFORM_COMMISSION_RATE',
            'platform_fee_address': 'PLATFORM_FEE_ADDRESS',
            'asset_creation_fee_amount': 'ASSET_CREATION_FEE_AMOUNT',
            'asset_creation_fee_address': 'ASSET_CREATION_FEE_ADDRESS'
        }
        
        # 验证和更新配置
        updated_configs = []
        for field_name, config_key in config_mapping.items():
            if field_name in data:
                value = data[field_name]
                
                # 数据验证
                if field_name == 'platform_commission_rate':
                    if not isinstance(value, (int, float)) or value < 0 or value > 1:
                        return jsonify({
                            'success': False,
                            'error': '平台分润比例必须在0-1之间'
                        }), 400
                        
                elif field_name in ['platform_fee_address', 'asset_creation_fee_address']:
                    if value and (not isinstance(value, str) or len(value) < 32):
                        return jsonify({
                            'success': False,
                            'error': f'{field_name}地址格式不正确'
                        }), 400
                        
                elif field_name == 'asset_creation_fee_amount':
                    if not isinstance(value, (int, float)) or value < 0:
                        return jsonify({
                            'success': False,
                            'error': '资产创建费用必须大于等于0'
                        }), 400
                
                # 更新配置
                old_value = SystemConfig.get_value(config_key)
                SystemConfig.set_value(config_key, str(value))
                
                updated_configs.append({
                    'key': config_key,
                    'old_value': old_value,
                    'new_value': str(value)
                })
        
        # 提交数据库更改
        db.session.commit()
        
        current_app.logger.info(f"支付配置已更新: {updated_configs}")
        
        return jsonify({
            'success': True,
            'message': '配置更新成功',
            'data': {
                'updated_count': len(updated_configs),
                'updated_configs': updated_configs
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新支付配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '更新支付配置失败'
        }), 500

@payment_management_bp.route('/api/v2/payment-config/history', methods=['GET'])
@api_admin_required
def get_payment_config_history():
    """获取支付配置变更历史"""
    try:
        # 这里可以实现配置变更历史记录
        # 暂时返回空数据，后续可以添加配置变更日志表
        return jsonify({
            'success': True,
            'data': []
        })
        
    except Exception as e:
        current_app.logger.error(f"获取配置历史失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取配置历史失败'
        }), 500