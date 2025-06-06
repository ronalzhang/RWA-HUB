from flask import Blueprint, jsonify, request, current_app
from app.extensions import db
from app.models import Asset
from app.utils.decorators import is_admin
import json
from datetime import datetime

bp = Blueprint('dividend', __name__)

@bp.route('/api/dividend/stats/<string:token_symbol>')
def get_dividend_stats(token_symbol):
    """获取分红统计信息"""
    try:
        # 简化版本，返回基本统计
        return jsonify({
            'count': 0,
            'total_amount': 0,
            'holder_count': 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/history/<string:token_symbol>')
def get_dividend_history(token_symbol):
    """获取分红历史记录"""
    try:
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/check_permission/<string:token_symbol>')
def check_permission(token_symbol):
    """检查用户是否有权限管理分红"""
    try:
        # 获取用户地址
        eth_address = request.headers.get('X-Eth-Address')
        if not eth_address:
            return jsonify({'has_permission': False}), 200
            
        # 检查管理员权限
        is_admin_user = is_admin(eth_address)
        
        # 如果是管理员，直接通过
        if is_admin_user:
            return jsonify({'has_permission': True, 'reason': 'admin'})
            
        # 检查是否是资产所有者
        try:
            asset = Asset.query.filter_by(token_symbol=token_symbol).first()
            if asset and asset.owner_address:
                # 对ETH地址（0x开头）忽略大小写比较
                if eth_address.startswith('0x') and asset.owner_address.startswith('0x'):
                    is_owner = eth_address.lower() == asset.owner_address.lower()
                # 对SOL地址严格区分大小写
                else:
                    is_owner = eth_address == asset.owner_address
                    
                if is_owner:
                    return jsonify({'has_permission': True, 'reason': 'owner'})
        except Exception as e:
            current_app.logger.warning(f"检查资产所有者权限时出错: {str(e)}")
            
        # 都不符合，无权限
        return jsonify({'has_permission': False, 'reason': 'unauthorized'})
            
    except Exception as e:
        current_app.logger.error(f"检查分红权限出错: {str(e)}")
        return jsonify({'has_permission': False, 'reason': 'error'})

@bp.route('/api/dividend/distribute/<string:token_symbol>', methods=['POST'])
def distribute_dividend(token_symbol):
    """发起分红"""
    try:
        return jsonify({'error': '分红功能暂未实现'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/claimable/<string:token_symbol>')
def get_claimable_dividend(token_symbol):
    """获取可领取的分红金额"""
    try:
        return jsonify({'amount': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/withdraw', methods=['POST'])
def withdraw_dividend():
    """申请提现分红"""
    try:
        return jsonify({'error': '提现功能暂未实现'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/withdrawal/status/<int:withdrawal_id>')
def get_withdrawal_status(withdrawal_id):
    """获取提现申请状态"""
    try:
        return jsonify({'status': 'unknown'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500 