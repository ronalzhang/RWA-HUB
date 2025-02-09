from flask import render_template, send_from_directory, current_app, request, redirect, url_for
from . import main_bp, auth_bp, assets_bp
from .admin import admin_required, is_admin
from ..models import Asset
from ..models.asset import AssetStatus
from sqlalchemy import or_ as db_or
from ..models.user import User
from ..utils.rwa_scraper import get_rwa_stats
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange

# 默认的 RWA 统计数据
DEFAULT_RWA_STATS = {
    'total_rwa_onchain': '16.96',
    'total_rwa_change': '-1.32',
    'total_holders': '83,506',
    'holders_change': '+1.92',
    'total_issuers': '112',
    'total_stablecoin': '220.39'
}

class AssetForm(FlaskForm):
    # 基本信息
    name = StringField('Asset Name', validators=[DataRequired(), Length(max=100)])
    type = SelectField('Asset Type', choices=[('10', 'Real Estate'), ('20', 'Similar Assets')], validators=[DataRequired()])
    location = StringField('Asset Location', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Asset Description', validators=[DataRequired(), Length(max=1000)])
    
    # 不动产特有字段
    area = FloatField('Asset Area', validators=[
        NumberRange(min=0, max=1000000, message='Area must be between 0 and 1,000,000 square meters')
    ])
    
    # 类不动产特有字段
    token_supply = FloatField('Token Supply', validators=[
        NumberRange(min=0, max=100000000, message='Token supply must be between 0 and 100,000,000')
    ])
    
    # 通用价值信息
    total_value = FloatField('Total Value (USDC)', validators=[
        DataRequired(),
        NumberRange(min=0, max=1000000000, message='Total value must be between 0 and 1,000,000,000 USDC')
    ])
    token_price = FloatField('Token Price (USDC)', validators=[
        DataRequired(),
        NumberRange(min=0, max=1000000, message='Token price must be between 0 and 1,000,000 USDC')
    ])
    annual_revenue = FloatField('Annual Revenue (%)', validators=[
        DataRequired(),
        NumberRange(min=0, max=100, message='Annual revenue must be between 0% and 100%')
    ])

    def validate(self):
        if not super().validate():
            return False
            
        if self.type.data == '10':  # 不动产
            if not self.area.data:
                self.area.errors.append('Area is required for real estate assets')
                return False
        else:  # 类不动产
            if not self.token_supply.data:
                self.token_supply.errors.append('Token supply is required for similar assets')
                return False
                
        return True

# 主页路由
@main_bp.route('/')
def index():
    """首页"""
    try:
        current_app.logger.info("开始处理首页请求")
        
        # 获取最新6个已上链资产
        assets = Asset.query.filter_by(status=2).order_by(Asset.created_at.desc()).limit(6).all()
        current_app.logger.info(f"获取到 {len(assets)} 个已上链资产")
        
        # 获取 RWA 统计数据
        try:
            current_app.logger.info("开始获取 RWA 统计数据")
            rwa_stats = get_rwa_stats()
            current_app.logger.info(f"获取到 RWA 统计数据: {rwa_stats}")
            
            if rwa_stats is None:
                current_app.logger.warning('获取 RWA 统计数据失败，使用默认值')
                rwa_stats = DEFAULT_RWA_STATS
        except Exception as e:
            current_app.logger.error(f'获取 RWA 统计数据出错: {str(e)}')
            rwa_stats = DEFAULT_RWA_STATS
        
        # 获取资产所有者信息
        asset_data = []
        for asset in assets:
            owner = User.query.filter_by(eth_address=asset.owner_address).first()
            asset_data.append({
                'id': asset.id,
                'name': asset.name,
                'price': asset.token_price,  # 使用 token_price 替代 price
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
        
        current_app.logger.info("准备渲染首页模板")
        return render_template('index.html', 
                             assets=asset_data, 
                             rwa_stats=rwa_stats,
                             current_user_address=request.headers.get('X-Eth-Address'))
                             
    except Exception as e:
        current_app.logger.error(f'处理首页请求失败: {str(e)}')
        return render_template('index.html', 
                             assets=[],
                             rwa_stats=DEFAULT_RWA_STATS,  # 确保在异常情况下也传递 rwa_stats
                             current_user_address=request.headers.get('X-Eth-Address'))

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
    form = AssetForm()
    return render_template('assets/create.html', form=form)

@assets_bp.route('/<int:asset_id>')
def asset_detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    return render_template('assets/detail.html', asset=asset)

# 管理页面路由
@assets_bp.route('/manage')
def manage_assets():
    return render_template('assets/manage.html')
