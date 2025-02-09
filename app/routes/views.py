from flask import render_template, send_from_directory, current_app, request, redirect, url_for
from . import main_bp, auth_bp, assets_bp
from .admin import admin_required, is_admin
from ..models import Asset
from ..models.asset import AssetStatus
from sqlalchemy import or_ as db_or
from ..models.user import User
from ..utils.rwa_scraper import get_rwa_stats

# 主页路由
@main_bp.route('/')
def index():
    """首页"""
    try:
        # 获取最新6个已上链资产
        assets = Asset.query.filter_by(status=2).order_by(Asset.created_at.desc()).limit(6).all()
        
        # 获取 RWA 统计数据
        rwa_stats = get_rwa_stats() or {
            'total_rwa_onchain': '16.96',
            'total_rwa_change': '-1.32',
            'total_holders': '83,506',
            'holders_change': '+1.92',
            'total_issuers': '112',
            'total_stablecoin': '220.39'
        }
        
        # 获取资产所有者信息
        asset_data = []
        for asset in assets:
            owner = User.query.filter_by(eth_address=asset.owner_address).first()
            asset_data.append({
                'id': asset.id,
                'name': asset.name,
                'price': asset.price,
                'images': asset.images if asset.images else ['/static/images/placeholder.jpg'],
                'owner_name': owner.name if owner else '未知用户',
                'status': asset.status,
                'token_symbol': asset.token_symbol,
                'location': asset.location,
                'asset_type': asset.asset_type,
                'area': asset.area,
                'total_value': asset.total_value,
                'token_price': asset.token_price,
                'annual_revenue': asset.annual_revenue
            })
        
        return render_template('index.html', assets=asset_data, rwa_stats=rwa_stats)
                             
    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}')
        return render_template('index.html', 
                             assets=[],
                             current_user_address=None)

# 静态文件路由
@main_bp.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(current_app.static_folder, filename)

# 认证页面路由
@auth_bp.route('/login')
def login():
    return render_template('auth/login.html')

@auth_bp.route('/register')
def register():
    return render_template('auth/register.html')

# 资产页面路由
@assets_bp.route('/create')
def create_asset():
    return render_template('assets/create.html')

@assets_bp.route('/<int:asset_id>')
def asset_detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    return render_template('assets/detail.html', asset=asset)

# 管理页面路由
@assets_bp.route('/manage')
def manage_assets():
    return render_template('assets/manage.html')
