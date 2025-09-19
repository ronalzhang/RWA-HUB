from flask import render_template, request, current_app
from flask_babel import gettext as _
from flask_wtf.csrf import generate_csrf
from sqlalchemy.orm import defer
from ..extensions import db
from ..models.asset import Asset, AssetStatus
from ..models.user import User
from ..models.news_hotspot import NewsHotspot
from ..utils import is_admin
from . import main_bp

# 创建一个简单的用户对象模拟
class MockUser:
    def __init__(self):
        self.is_authenticated = False
        self.username: str | None = None

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
        
        # 显示状态为2（APPROVED/ON_CHAIN）且未删除的资产
        query = Asset.query.filter(
            Asset.status == 2,  # 直接使用数值2，避免枚举问题
            Asset.deleted_at.is_(None)
        )
            
        # 获取最新3个资产
        assets = query.order_by(Asset.created_at.desc()).limit(3).all()
        current_app.logger.info(f'获取资产列表: 找到 {len(assets)} 个资产，查询条件: status=2, deleted_at IS NULL')
        
        # 调试信息
        if len(assets) == 0:
            total_assets = Asset.query.count()
            status_2_assets = Asset.query.filter(Asset.status == 2).count()
            current_app.logger.error(f'首页无资产显示 - 总资产数: {total_assets}, status=2的资产数: {status_2_assets}')
        
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

@main_bp.route('/v6')
def index_v6():
    """v6版本首页"""
    try:
        # 获取当前用户的钱包地址（从多个来源）
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_args = request.args.get('eth_address')
        
        # 优先使用 Args > Header > Cookie
        eth_address = eth_address_args or eth_address_header or eth_address_cookie
        
        current_app.logger.info(f'V6界面 - 钱包地址来源:')
        current_app.logger.info(f'- Header: {eth_address_header}')
        current_app.logger.info(f'- Cookie: {eth_address_cookie}')
        current_app.logger.info(f'- Args: {eth_address_args}')
        current_app.logger.info(f'最终使用地址: {eth_address}')
        
        # 显示状态为2（APPROVED/ON_CHAIN）且未删除的资产  
        query = Asset.query.filter(
            Asset.status == 2,
            Asset.deleted_at.is_(None)
        )
            
        # 获取最新3个资产
        assets = query.order_by(Asset.created_at.desc()).limit(3).all()
        current_app.logger.info(f'V6界面 - 获取资产列表成功: 找到 {len(assets)} 个资产')
        
        # 创建模拟的current_user对象
        mock_user = MockUser()
        if eth_address:
            mock_user.is_authenticated = True
            mock_user.username = eth_address[:10] + "..."  # 简化显示
        
        # 使用v6版本的模板
        return render_template('index_v6.html', 
                             assets=assets,
                             current_user_address=eth_address,
                             current_user=mock_user,  # 添加current_user变量
                             AssetStatus=AssetStatus,
                             csrf_token=generate_csrf,  # 添加CSRF token
                             _=_)
                             
    except Exception as e:
        current_app.logger.error(f'V6界面 - 获取资产列表失败: {str(e)}')
        # 创建模拟的current_user对象
        mock_user = MockUser()
        
        return render_template('index_v6.html', 
                             assets=[],
                             current_user_address=None,
                             current_user=mock_user,  # 添加current_user变量
                             AssetStatus=AssetStatus,
                             csrf_token=generate_csrf,  # 添加CSRF token
                             _=_)

@main_bp.route('/portfolio')
def portfolio():
    """用户投资组合页面"""
    try:
        # 获取当前用户的钱包地址
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_args = request.args.get('eth_address')

        # 优先使用 Args > Header > Cookie
        eth_address = eth_address_args or eth_address_header or eth_address_cookie

        current_app.logger.info(f'投资组合页面 - 钱包地址: {eth_address}')

        # 渲染投资组合页面
        return render_template('portfolio.html',
                             current_user_address=eth_address,
                             _=_)

    except Exception as e:
        current_app.logger.error(f'加载投资组合页面失败: {str(e)}')
        return render_template('portfolio.html',
                             current_user_address=None,
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

@main_bp.route('/news/<int:news_id>')
def news_detail(news_id):
    """新闻详情页面"""
    try:
        # 根据ID查找新闻热点
        hotspot = NewsHotspot.query.filter_by(id=news_id, is_active=True).first()
        if not hotspot:
            current_app.logger.warning(f'新闻详情页面 - 未找到ID为{news_id}的热点新闻')
            return render_template('404.html'), 404

        # 获取相关新闻（同分类，排除当前新闻）
        related_news = NewsHotspot.query.filter(
            NewsHotspot.category == hotspot.category,
            NewsHotspot.is_active == True,
            NewsHotspot.id != news_id
        ).order_by(NewsHotspot.created_at.desc()).limit(3).all()

        current_app.logger.info(f'显示新闻详情: {hotspot.title}')

        return render_template('news_detail.html',
                             hotspot=hotspot,
                             related_news=related_news,
                             _=_)

    except Exception as e:
        current_app.logger.error(f'加载新闻详情页面失败: {str(e)}')
        return render_template('404.html'), 404
