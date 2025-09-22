from flask import render_template, request, current_app
from flask_babel import gettext as _
from ..models.asset import Asset, AssetStatus
from ..models.user import User
from ..utils import is_admin
from . import main_bp

# 引入统一的资产过滤函数
from .assets import get_filtered_assets_query

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

        # 检查是否是管理员
        is_admin_user = is_admin(eth_address) if eth_address else False

        # 使用统一的资产过滤函数
        query = get_filtered_assets_query(eth_address, is_admin_user)

        # 获取最新3个资产
        assets = query.order_by(Asset.created_at.desc()).limit(3).all()
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

# 在文件末尾添加favicon路由
@main_bp.route('/favicon.ico')
def favicon():
    """提供favicon.ico文件"""
    from flask import send_from_directory
    import os
    try:
        return send_from_directory(os.path.join(current_app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except FileNotFoundError:
        return '', 404
