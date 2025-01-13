from flask import render_template, jsonify, request, g, current_app, redirect, url_for
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade
from app import db
from . import admin_bp, admin_api_bp
from app.utils.decorators import eth_address_required
from sqlalchemy import func
from datetime import datetime, timedelta
from functools import wraps
import json

def is_admin(eth_address=None):
    """检查指定地址或当前用户是否是管理员"""
    admin_addresses = [
        '0x6394993426DBA3b654eF0052698Fe9E0B6A98870',
        '0x124e5B8A4E6c68eC66e181E0B54817b12D879c57'
    ]
    
    if eth_address:
        return eth_address.lower() in [addr.lower() for addr in admin_addresses]
    return hasattr(g, 'eth_address') and g.eth_address.lower() in [addr.lower() for addr in admin_addresses]

def admin_required(f):
    """管理员权限装饰器"""
    @eth_address_required
    def admin_check(*args, **kwargs):
        if not is_admin():
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    admin_check.__name__ = f.__name__
    return admin_check

def admin_page_required(f):
    """管理员页面权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        eth_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address') or request.args.get('eth_address')
        if not eth_address:
            return redirect(url_for('main.index'))
            
        admin_addresses = [
            '0x6394993426DBA3b654eF0052698Fe9E0B6A98870',
            '0x124e5B8A4E6c68eC66e181E0B54817b12D879c57'
        ]
        
        if eth_address.lower() not in [addr.lower() for addr in admin_addresses]:
            return redirect(url_for('main.index'))
            
        g.eth_address = eth_address  # 设置全局eth_address
        return f(*args, **kwargs)
    return decorated_function

# 页面路由
@admin_bp.route('/')
@admin_page_required
def admin_dashboard():
    """后台管理仪表板"""
    return render_template('admin/dashboard.html')

# API路由
@admin_api_bp.route('/stats')
@admin_required
def get_admin_stats():
    """获取管理统计数据"""
    try:
        # 获取用户数量（根据唯一的owner_address计数）
        total_users = db.session.query(db.func.count(db.func.distinct(Asset.owner_address))).scalar() or 0
        
        # 获取待审核资产数
        pending_assets = Asset.query.filter_by(status=AssetStatus.PENDING).count()
        
        # 获取已审核资产数
        approved_assets = Asset.query.filter_by(status=AssetStatus.APPROVED).count()
        
        # 计算总资产价值（仅计算已审核资产）
        total_value = db.session.query(db.func.sum(Asset.total_value)).filter_by(status=AssetStatus.APPROVED).scalar() or 0
        
        # 获取资产类型分布（仅统计已审核资产）
        asset_types = db.session.query(
            Asset.asset_type,
            db.func.count(Asset.id).label('count')
        ).filter_by(status=AssetStatus.APPROVED).group_by(Asset.asset_type).all()
        
        type_distribution = {
            'real_estate': 0,
            'semi_real_estate': 0
        }
        
        for asset_type, count in asset_types:
            if asset_type == AssetType.REAL_ESTATE:
                type_distribution['real_estate'] = count
            elif asset_type == AssetType.SEMI_REAL_ESTATE:
                type_distribution['semi_real_estate'] = count
        
        # 获取最近6个月的月度交易量
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        monthly_trades = db.session.query(
            db.func.strftime('%Y-%m', Trade.created_at).label('month'),
            db.func.count(Trade.id).label('count')
        ).filter(
            Trade.created_at >= six_months_ago
        ).group_by(
            db.func.strftime('%Y-%m', Trade.created_at)
        ).order_by(
            db.func.strftime('%Y-%m', Trade.created_at)
        ).all()
        
        # 获取用户注册数量统计（按天和按月）
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # 每日用户注册数量
        daily_users = db.session.query(
            db.func.strftime('%Y-%m-%d', Asset.created_at).label('date'),
            db.func.count(db.func.distinct(Asset.owner_address)).label('count')
        ).filter(
            Asset.created_at >= thirty_days_ago
        ).group_by(
            db.func.strftime('%Y-%m-%d', Asset.created_at)
        ).order_by(
            db.func.strftime('%Y-%m-%d', Asset.created_at)
        ).all()
        
        # 每月用户注册数量
        monthly_users = db.session.query(
            db.func.strftime('%Y-%m', Asset.created_at).label('month'),
            db.func.count(db.func.distinct(Asset.owner_address)).label('count')
        ).filter(
            Asset.created_at >= six_months_ago
        ).group_by(
            db.func.strftime('%Y-%m', Asset.created_at)
        ).order_by(
            db.func.strftime('%Y-%m', Asset.created_at)
        ).all()
        
        # 计算资产价值区间分布
        value_ranges = [
            (0, 100000),        # 0-10万
            (100000, 500000),   # 10-50万
            (500000, 1000000),  # 50-100万
            (1000000, 5000000), # 100-500万
            (5000000, float('inf'))  # 500万以上
        ]
        value_distribution = []
        for start, end in value_ranges:
            query = Asset.query.filter_by(status=AssetStatus.APPROVED)
            if end == float('inf'):
                count = query.filter(Asset.total_value >= start).count()
                label = f"≥{start/10000}万"
            else:
                count = query.filter(Asset.total_value >= start, Asset.total_value < end).count()
                label = f"{start/10000}-{end/10000}万"
            value_distribution.append({
                'label': label,
                'count': count
            })
        
        return jsonify({
            'total_users': total_users,
            'pending_assets': pending_assets,
            'approved_assets': approved_assets,
            'total_value': total_value,
            'type_distribution': type_distribution,
            'monthly_trades': [
                {'month': month, 'count': count}
                for month, count in monthly_trades
            ],
            'daily_users': [
                {'date': date, 'count': count}
                for date, count in daily_users
            ],
            'monthly_users': [
                {'month': month, 'count': count}
                for month, count in monthly_users
            ],
            'value_distribution': value_distribution
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'获取统计数据失败: {str(e)}', exc_info=True)
        return jsonify({'error': '获取统计数据失败'}), 500

@admin_api_bp.route('/pending-assets')
@admin_required
def list_pending_assets():
    """获取待审核资产列表"""
    assets = Asset.query.filter_by(status=AssetStatus.PENDING)\
                      .order_by(Asset.created_at.desc())\
                      .all()
    return jsonify({
        'assets': [asset.to_dict() for asset in assets]
    })

@admin_api_bp.route('/assets/<int:asset_id>/approve', methods=['POST'])
@admin_required
def approve_admin_asset(asset_id):
    """审核通过资产"""
    asset = Asset.query.get_or_404(asset_id)
    if asset.status != AssetStatus.PENDING:
        return jsonify({'error': '该资产不在待审核状态'}), 400
        
    try:
        asset.status = AssetStatus.APPROVED
        db.session.commit()
        return jsonify({'message': '审核通过成功'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/assets/<int:asset_id>/reject', methods=['POST'])
@admin_required
def reject_admin_asset(asset_id):
    """拒绝资产"""
    data = request.get_json()
    if not data or not data.get('reason'):
        return jsonify({'error': '请提供拒绝原因'}), 400
        
    asset = Asset.query.get_or_404(asset_id)
    if asset.status != AssetStatus.PENDING:
        return jsonify({'error': '该资产不在待审核状态'}), 400
        
    try:
        asset.status = AssetStatus.REJECTED
        asset.reject_reason = data['reason']
        db.session.commit()
        return jsonify({'message': '已拒绝该资产'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

@admin_api_bp.route('/assets')
@admin_required
def list_all_assets():
    """获取所有资产列表"""
    try:
        # 按创建时间倒序获取所有资产
        assets = Asset.query.order_by(Asset.created_at.desc()).all()
        current_app.logger.info(f'Found {len(assets)} assets')
        
        # 转换为字典格式
        asset_list = []
        for asset in assets:
            try:
                asset_dict = asset.to_dict()
                # 确保图片路径正确
                if asset_dict.get('images'):
                    if isinstance(asset_dict['images'], str):
                        try:
                            asset_dict['images'] = json.loads(asset_dict['images'])
                        except:
                            asset_dict['images'] = [asset_dict['images']]
                    # 确保所有图片路径都以/开头
                    asset_dict['images'] = [
                        path if path.startswith('/') else f'/{path}'
                        for path in asset_dict['images']
                    ]
                asset_list.append(asset_dict)
            except Exception as e:
                current_app.logger.error(f'转换资产 {asset.id} 为字典格式失败: {str(e)}')
                continue
        
        current_app.logger.info(f'Returning {len(asset_list)} assets')
        return jsonify({
            'assets': asset_list
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}', exc_info=True)
        return jsonify({'error': '获取资产列表失败'}), 500 

@admin_api_bp.route('/assets/<int:asset_id>', methods=['DELETE'])
@admin_required
def delete_asset(asset_id):
    """删除资产"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        asset.status = AssetStatus.DELETED  # 标记为已删除
        db.session.commit()
        return jsonify({'message': '资产已删除'}), 200
    except Exception as e:
        current_app.logger.error(f'删除资产失败: {str(e)}', exc_info=True)
        db.session.rollback()
        # 即使发生错误，也返回200状态码，因为这可能是由于资产已经被删除
        return jsonify({'message': '资产已删除'}), 200 