from flask import render_template, send_from_directory, current_app, request, redirect, url_for, flash, session
from . import main_bp, assets_bp
from .admin import admin_required
from app.utils.admin import is_admin
from ..models import Asset
from ..models.asset import AssetStatus
from sqlalchemy import or_ as db_or
from app.models.trade import Trade, TradeStatus
from app.models import ShortLink
import logging

# 主页路由
# @main_bp.route('/')
# def index():
#     """首页"""
#     try:
#         # 获取当前用户的钱包地址
#         eth_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address')
#         current_app.logger.info(f'当前用户钱包地址: {eth_address}')
#         
#         # 构建查询条件
#         current_app.logger.info(f'查询条件: eth_address={eth_address}')
#         
#         # 获取资产列表
#         query = Asset.query
#         
#         # 如果是管理员，显示所有未删除的资产
#         if eth_address and is_admin(eth_address):
#             query = query.filter(Asset.status != AssetStatus.DELETED.value)
#         else:
#             # 非管理员只能看到已审核通过的资产
#             query = query.filter(Asset.status == AssetStatus.APPROVED.value)
#             
#         assets = query.order_by(Asset.created_at.desc()).limit(6).all()
#         
#         current_app.logger.info(f'获取资产列表成功: 找到 {len(assets)} 个资产')
#         current_app.logger.info(f'资产状态: {[asset.status for asset in assets]}')
#         
#         return render_template('index.html', 
#                              assets=assets,
#                              current_user_address=eth_address)
#                              
#     except Exception as e:
#         current_app.logger.error(f'获取资产列表失败: {str(e)}')
#         return render_template('index.html', 
#                              assets=[],
#                              current_user_address=None)

# 静态文件路由
@main_bp.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(current_app.static_folder, filename)

# 资产页面路由
@assets_bp.route('/create')
def create_asset():
    return render_template('assets/create.html')

# 管理页面路由
@assets_bp.route('/manage')
def manage_assets():
    return render_template('assets/manage.html')

# 添加短链接处理路由
@main_bp.route('/s/<code>')
def shortlink_redirect(code):
    """处理短链接重定向"""
    short_link = ShortLink.query.filter_by(code=code).first()
    
    if not short_link:
        flash('无效的短链接', 'error')
        return redirect(url_for('main.index'))
    
    if short_link.is_expired():
        flash('此链接已过期', 'error')
        return redirect(url_for('main.index'))
    
    # 增加点击计数
    short_link.increment_click()
    
    # 重定向到原始URL
    return redirect(short_link.original_url) 
