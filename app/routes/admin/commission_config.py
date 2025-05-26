"""
佣金配置管理API
管理35%分佣规则、分享按钮设置等配置
"""
from flask import Blueprint, request, jsonify, current_app
from app.models import db
from app.models.commission_config import CommissionConfig, UserCommissionBalance
from app.utils.auth import admin_required
from datetime import datetime

commission_config_bp = Blueprint('commission_config', __name__)

@commission_config_bp.route('/api/admin/commission/config', methods=['GET'])
@admin_required
def get_commission_config():
    """获取佣金配置"""
    try:
        configs = {
            # 35%分佣规则配置
            'commission_rate': CommissionConfig.get_config('commission_rate', 35.0),
            'commission_description': CommissionConfig.get_config('commission_description', '推荐好友享受35%佣金奖励'),
            
            # 分享按钮配置
            'share_button_text': CommissionConfig.get_config('share_button_text', '分享赚佣金'),
            'share_description': CommissionConfig.get_config('share_description', '分享此项目给好友，好友购买后您将获得35%佣金奖励'),
            'share_success_message': CommissionConfig.get_config('share_success_message', '分享链接已复制，快去邀请好友吧！'),
            
            # 提现配置
            'min_withdraw_amount': CommissionConfig.get_config('min_withdraw_amount', 10.0),
            'withdraw_fee_rate': CommissionConfig.get_config('withdraw_fee_rate', 0.0),
            'withdraw_description': CommissionConfig.get_config('withdraw_description', '最低提现金额10 USDC，提现将转入您的钱包地址'),
            
            # 佣金计算规则说明
            'commission_rules': CommissionConfig.get_config('commission_rules', {
                'direct_commission': '直接推荐佣金：好友购买金额的35%',
                'indirect_commission': '间接推荐佣金：下级佣金收益的35%',
                'settlement_time': '佣金实时到账，可随时提现',
                'currency': 'USDC'
            })
        }
        
        return jsonify({
            'success': True,
            'data': configs
        })
        
    except Exception as e:
        current_app.logger.error(f"获取佣金配置失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@commission_config_bp.route('/api/admin/commission/config', methods=['POST'])
@admin_required
def update_commission_config():
    """更新佣金配置"""
    try:
        data = request.get_json()
        
        # 更新各项配置
        config_mappings = {
            'commission_rate': ('佣金比例', '推荐佣金比例设置'),
            'commission_description': ('佣金描述', '佣金功能描述文案'),
            'share_button_text': ('分享按钮文案', '分享按钮显示文案'),
            'share_description': ('分享说明', '分享功能说明文案'),
            'share_success_message': ('分享成功提示', '分享成功后的提示信息'),
            'min_withdraw_amount': ('最低提现金额', '用户提现的最低金额限制'),
            'withdraw_fee_rate': ('提现手续费率', '提现时收取的手续费比例'),
            'withdraw_description': ('提现说明', '提现功能说明文案'),
            'commission_rules': ('佣金规则', '佣金计算规则详细说明')
        }
        
        updated_configs = []
        for key, value in data.items():
            if key in config_mappings:
                description = config_mappings[key][1]
                CommissionConfig.set_config(key, value, description)
                updated_configs.append(config_mappings[key][0])
        
        return jsonify({
            'success': True,
            'message': f'已更新配置: {", ".join(updated_configs)}',
            'updated_count': len(updated_configs)
        })
        
    except Exception as e:
        current_app.logger.error(f"更新佣金配置失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@commission_config_bp.route('/api/commission/share-config', methods=['GET'])
def get_share_config():
    """获取分享配置（前端调用）"""
    try:
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

@commission_config_bp.route('/api/user/commission/balance/<address>', methods=['GET'])
def get_user_commission_balance(address):
    """获取用户佣金余额（钱包显示）"""
    try:
        balance = UserCommissionBalance.get_balance(address)
        
        return jsonify({
            'success': True,
            'data': balance.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"获取用户佣金余额失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@commission_config_bp.route('/api/user/commission/withdraw', methods=['POST'])
def withdraw_commission():
    """提现佣金"""
    try:
        data = request.get_json()
        user_address = data.get('user_address')
        amount = float(data.get('amount', 0))
        to_address = data.get('to_address')  # 提现到的钱包地址
        
        if not user_address or not to_address or amount <= 0:
            return jsonify({'error': '参数错误'}), 400
        
        # 检查最低提现金额
        min_withdraw = CommissionConfig.get_config('min_withdraw_amount', 10.0)
        if amount < min_withdraw:
            return jsonify({'error': f'最低提现金额为 {min_withdraw} USDC'}), 400
        
        # 更新余额
        balance = UserCommissionBalance.update_balance(user_address, amount, 'withdraw')
        
        # TODO: 这里需要实际的区块链转账逻辑
        # 暂时只记录提现请求
        
        return jsonify({
            'success': True,
            'message': f'提现申请已提交，{amount} USDC 将转入 {to_address}',
            'data': balance.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"提现失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500 