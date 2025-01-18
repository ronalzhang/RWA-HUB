from flask import render_template
from ..models.asset import Asset
from ..models.user import User
from . import main_bp

@main_bp.route('/')
def index():
    """首页"""
    # 获取最新6个已审核资产
    assets = Asset.query.filter_by(status=1).order_by(Asset.created_at.desc()).limit(6).all()
    
    # 获取资产所有者信息
    asset_data = []
    for asset in assets:
        owner = User.query.filter_by(eth_address=asset.owner).first()
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
    
    return render_template('index.html', assets=asset_data)

@main_bp.route('/auth/login')
def login():
    """登录页面"""
    return render_template('auth/login.html')

@main_bp.route('/auth/register')
def register():
    """注册页面"""
    return render_template('auth/register.html')
