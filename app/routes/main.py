from flask import render_template, request, current_app
from flask_babel import gettext as _
from ..models.asset import Asset, AssetStatus
from ..models.user import User
from ..utils import is_admin
from . import main_bp
from datetime import datetime, timedelta
from sqlalchemy import and_
from app.models.news_hotspot import NewsHotspot
from app.extensions import db

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


@main_bp.route('/news/<int:year>/<int:month>/<int:day>/<string:slug>')
def news_detail(year, month, day, slug):
    """新闻详情页：按日期与slug匹配 NewsHotspot 并渲染详情模板"""
    try:
        # 解析日期边界（UTC）
        start_dt = datetime(year, month, day)
        end_dt = start_dt + timedelta(days=1)

        # 同日范围内按slug匹配（对比标题经相同规则slug化）
        # 为避免在SQL中实现slug化，先获取当日候选记录再在Python中过滤，日数据通常很小
        candidates = NewsHotspot.query.filter(
            and_(
                NewsHotspot.created_at >= start_dt,
                NewsHotspot.created_at < end_dt,
                NewsHotspot.is_active == True
            )
        ).order_by(NewsHotspot.created_at.desc()).all()

        import re
        def to_slug(text: str) -> str:
            text = (text or '').strip().lower()
            text = re.sub(r"\s+", "-", text)
            text = re.sub(r"[^a-z0-9-]", "", text)
            text = re.sub(r"-+", "-", text)
            return text.strip('-')

        target = None
        for item in candidates:
            if to_slug(item.title) == slug:
                target = item
                break

        if not target:
            current_app.logger.warning(f"新闻未找到: date={year}-{month}-{day}, slug={slug}")
            return render_template('error.html', error=_('News not found')), 404

        # 访问量+1
        try:
            target.increment_view_count()
        except Exception as inc_err:
            current_app.logger.warning(f"新闻访问量更新失败: {str(inc_err)}")

        # 推荐新闻
        related_news = []
        try:
            related_news = NewsHotspot.get_recommended_news(target.id, limit=2)
        except Exception as rec_err:
            current_app.logger.warning(f"获取推荐新闻失败: {str(rec_err)}")

        # 获取当前用户地址（与首页一致来源）
        eth_address = request.args.get('eth_address') or \
                      request.headers.get('X-Eth-Address') or \
                      request.cookies.get('eth_address')

        return render_template('news_detail.html', hotspot=target, related_news=related_news, current_user_address=eth_address)

    except Exception as e:
        current_app.logger.error(f"新闻详情页异常: {str(e)}")
        return render_template('error.html', error=_('Error rendering news page')), 500

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
