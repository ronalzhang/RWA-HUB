from flask import render_template, request, current_app
from flask_babel import gettext as _
from ..models.asset import Asset, AssetStatus
from ..models.user import User
from ..utils import is_admin
from . import main_bp

@main_bp.route('/')
def index():
    """首页"""
    try:
        # 获取当前用户的钱包地址
        eth_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address')
        current_app.logger.info(f'当前用户钱包地址: {eth_address}')
        
        # 构建查询条件
        query = Asset.query
        
        # 如果是管理员，显示所有未删除的资产
        if eth_address and is_admin(eth_address):
            query = query.filter(Asset.status != AssetStatus.DELETED.value)
        else:
            # 非管理员只能看到已审核通过的资产
            query = query.filter(Asset.status == AssetStatus.APPROVED.value)
            
        # 获取最新6个资产
        assets = query.order_by(Asset.created_at.desc()).limit(6).all()
        current_app.logger.info(f'获取资产列表成功: 找到 {len(assets)} 个资产')
        
        # 获取资产所有者信息
        asset_data = []
        for asset in assets:
            owner = User.query.filter_by(eth_address=asset.owner_address).first()
            asset_data.append({
                'id': asset.id,
                'name': asset.name,
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
        
        return render_template('index.html', 
                             assets=asset_data,
                             current_user_address=eth_address,
                             AssetStatus=AssetStatus,
                             _=_)
                             
    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}')
        return render_template('index.html', 
                             assets=[],
                             current_user_address=None,
                             AssetStatus=AssetStatus,
                             _=_)

@main_bp.route('/auth/login')
def login():
    """登录页面"""
    return render_template('auth/login.html', _=_)

@main_bp.route('/auth/register')
def register():
    """注册页面"""
    return render_template('auth/register.html', _=_)
