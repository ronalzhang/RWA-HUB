from flask import Blueprint, jsonify, request, current_app
from app.models.dividend import DividendRecord, DividendDistribution, WithdrawalRequest
from app.models.asset import Asset
from app.models.user import User
from app.utils.solana import get_solana_client
from app.utils.auth import login_required
from app.utils.wallet import get_wallet_balance
from app.extensions import db
import json
from datetime import datetime

bp = Blueprint('dividend', __name__)

@bp.route('/api/dividend/stats/<string:token_symbol>')
@login_required
def get_dividend_stats(token_symbol):
    """获取分红统计信息"""
    try:
        asset = Asset.query.filter_by(symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404
            
        count = DividendRecord.get_count_by_asset(asset.id)
        total_amount = DividendRecord.get_total_amount_by_asset(asset.id)
        holder_count = len(asset.holders)
        
        return jsonify({
            'count': count,
            'total_amount': total_amount,
            'holder_count': holder_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/history/<string:token_symbol>')
@login_required
def get_dividend_history(token_symbol):
    """获取分红历史记录"""
    try:
        asset = Asset.query.filter_by(symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404
            
        records = DividendRecord.get_by_asset(asset.id)
        return jsonify([record.to_dict() for record in records])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/check_permission/<string:token_symbol>')
@login_required
def check_permission(token_symbol):
    """检查用户是否有权限管理分红"""
    try:
        asset = Asset.query.filter_by(symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404
            
        user = User.query.get(current_user.id)
        has_permission = user.is_admin or asset.owner_address == user.wallet_address
        
        return jsonify({'has_permission': has_permission})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/distribute/<string:token_symbol>', methods=['POST'])
@login_required
def distribute_dividend(token_symbol):
    """发起分红"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        interval = int(data.get('interval', 86400))  # 默认24小时
        
        if amount <= 0:
            return jsonify({'error': '分红金额必须大于0'}), 400
            
        asset = Asset.query.filter_by(symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404
            
        user = User.query.get(current_user.id)
        if not user.is_admin and asset.owner_address != user.wallet_address:
            return jsonify({'error': '没有权限管理该资产的分红'}), 403
            
        # 检查用户USDC余额
        client = get_solana_client()
        balance = client.get_token_account_balance(user.usdc_token_account)
        if balance < amount:
            return jsonify({'error': 'USDC余额不足'}), 400
            
        # 创建分红记录
        record = DividendRecord.create(
            asset_id=asset.id,
            amount=amount,
            distributor_address=user.wallet_address,
            interval=interval
        )
        
        # 调用智能合约
        try:
            tx_hash = client.transfer_dividend_to_platform(
                amount=amount,
                distributor=user.wallet_address,
                platform_address=current_app.config['PLATFORM_FEE_ADDRESS']
            )
            record.update_transaction_hash(tx_hash)
            db.session.commit()
            
            return jsonify({
                'message': '分红发起成功',
                'transaction_hash': tx_hash
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'智能合约调用失败: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/claimable/<string:token_symbol>')
@login_required
def get_claimable_dividend(token_symbol):
    """获取可领取的分红金额"""
    try:
        asset = Asset.query.filter_by(symbol=token_symbol).first()
        if not asset:
            return jsonify({'error': '资产不存在'}), 404
            
        user = User.query.get(current_user.id)
        distributions = DividendDistribution.query.filter_by(
            holder_address=user.wallet_address,
            status='pending'
        ).all()
        
        total_amount = sum(d.amount for d in distributions)
        return jsonify({'amount': total_amount})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/withdraw', methods=['POST'])
@login_required
def withdraw_dividend():
    """申请提现分红"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        
        if amount <= 0:
            return jsonify({'error': '提现金额必须大于0'}), 400
            
        user = User.query.get(current_user.id)
        
        # 检查可提现金额
        distributions = DividendDistribution.query.filter_by(
            holder_address=user.wallet_address,
            status='pending'
        ).all()
        
        available_amount = sum(d.amount for d in distributions)
        if amount > available_amount:
            return jsonify({'error': '可提现金额不足'}), 400
            
        # 创建提现申请
        withdrawal = WithdrawalRequest.create(
            user_address=user.wallet_address,
            amount=amount,
            type='dividend'
        )
        
        # 调用智能合约
        try:
            client = get_solana_client()
            tx_hash = client.process_withdrawal(
                amount=amount,
                user=user.wallet_address,
                platform_address=current_app.config['PLATFORM_FEE_ADDRESS']
            )
            withdrawal.update_transaction_hash(tx_hash)
            db.session.commit()
            
            return jsonify({
                'message': '提现申请成功',
                'transaction_hash': tx_hash
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'智能合约调用失败: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dividend/withdrawal/status/<int:withdrawal_id>')
@login_required
def get_withdrawal_status(withdrawal_id):
    """获取提现申请状态"""
    try:
        withdrawal = WithdrawalRequest.query.get(withdrawal_id)
        if not withdrawal:
            return jsonify({'error': '提现申请不存在'}), 404
            
        user = User.query.get(current_user.id)
        if withdrawal.user_address != user.wallet_address:
            return jsonify({'error': '无权查看该提现申请'}), 403
            
        return jsonify(withdrawal.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500 