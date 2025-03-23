from flask import render_template, send_from_directory, current_app, request, redirect, url_for, flash, session
from . import main_bp, auth_bp, assets_bp
from .admin import admin_required, is_admin
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
    """资产详情页面"""
    logger = logging.getLogger(__name__)
    
    logger.info(f"正在访问资产详情页面: asset_id={asset_id}")
    
    # 获取资产对象
    asset = Asset.query.get_or_404(asset_id)
    logger.info(f"获取资产数据成功: name='{asset.name}', token_symbol='{asset.token_symbol}', token_supply={asset.token_supply}")
    
    # 计算剩余供应量
    # 获取所有已完成的交易
    trades = Trade.query.filter_by(asset_id=asset.id, status=TradeStatus.COMPLETED.value).all()
    logger.info(f"查询到已完成交易数量: {len(trades)}")
    
    # 检查资产的token_supply
    if asset.token_supply is None or asset.token_supply <= 0:
        logger.warning(f"资产token_supply异常: {asset.token_supply}")
        
    # 计算已完成的交易总量
    completed_trades = []
    for trade in trades:
        logger.info(f"交易ID: {trade.id}, 数量: {trade.amount}, 状态: {trade.status}, 创建时间: {trade.created_at}")
        completed_trades.append({
            'id': trade.id,
            'amount': trade.amount,
            'status': trade.status
        })
    
    completed_amount = sum(trade.amount for trade in trades)
    logger.info(f"已完成交易总量: {completed_amount}")
    
    # 计算剩余供应量
    try:
        remaining_supply = asset.token_supply - completed_amount
        logger.info(f"计算得到剩余供应量: {remaining_supply} = {asset.token_supply} - {completed_amount}")
        
        # 防止负值
        if remaining_supply < 0:
            logger.warning(f"计算得到负的剩余供应量: {remaining_supply}，将设置为0")
            remaining_supply = 0
    except Exception as e:
        logger.error(f"计算剩余供应量时出错: {str(e)}")
        remaining_supply = 0
    
    logger.info(f"最终剩余供应量: {remaining_supply}")
    return render_template('assets/detail.html', asset=asset, remaining_supply=remaining_supply)

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
