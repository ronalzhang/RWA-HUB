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
        # 获取当前用户的钱包地址（从多个来源）
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_args = request.args.get('eth_address')
        
        # 优先使用 Args > Header > Cookie
        eth_address = eth_address_args or eth_address_header or eth_address_cookie
        
        current_app.logger.info(f'钱包地址来源:')
        current_app.logger.info(f'- Header: {eth_address_header}')
        current_app.logger.info(f'- Cookie: {eth_address_cookie}')
        current_app.logger.info(f'- Args: {eth_address_args}')
        current_app.logger.info(f'最终使用地址: {eth_address}')
        
        # 构建查询条件
        query = Asset.query
        
        # 如果是管理员，显示所有未删除的资产
        if eth_address and is_admin(eth_address):
            current_app.logger.info(f'管理员用户: {eth_address}，显示所有未删除资产')
            query = query.filter(Asset.status != AssetStatus.DELETED.value)
        else:
            # 非管理员只能看到已审核通过的资产
            current_app.logger.info('普通用户或未登录用户：只显示已审核通过的资产')
            query = query.filter(Asset.status == AssetStatus.APPROVED.value)
            
        # 获取最新6个资产
        assets = query.order_by(Asset.created_at.desc()).limit(6).all()
        current_app.logger.info(f'获取资产列表成功: 找到 {len(assets)} 个资产')
        
        # 直接使用ORM对象列表，不转换为字典
        return render_template('index.html', 
                             assets=assets,
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
