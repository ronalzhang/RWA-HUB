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
def news_detail_legacy(news_id):
    """新闻详情页面 - 兼容旧版本ID链接，重定向到新格式"""
    try:
        # 根据ID查找新闻热点
        hotspot = NewsHotspot.query.filter_by(id=news_id, is_active=True).first()
        if not hotspot:
            current_app.logger.warning(f'新闻详情页面 - 未找到ID为{news_id}的热点新闻')
            return render_template('404.html'), 404

        # 生成SEO友好的slug
        from urllib.parse import quote
        import re

        # 创建slug：移除特殊字符，替换空格为连字符
        slug = re.sub(r'[^\w\s-]', '', hotspot.title)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-').lower()

        # 如果slug为空或太短，使用默认值
        if not slug or len(slug) < 3:
            slug = f"news-{news_id}"

        # 构建新的URL格式并重定向
        from flask import redirect, url_for
        new_url = f"/news/{hotspot.created_at.strftime('%Y/%m/%d')}/{slug}"
        current_app.logger.info(f'重定向旧URL /news/{news_id} 到新URL {new_url}')
        return redirect(new_url, code=301)  # 永久重定向

    except Exception as e:
        current_app.logger.error(f'新闻详情页面 - 重定向失败: {str(e)}')
        return render_template('404.html'), 404

@main_bp.route('/news/<int:year>/<int:month>/<int:day>/<slug>')
def news_detail(year, month, day, slug):
    """基于日期的新闻详情页面 - SEO友好的URL格式"""
    try:
        from datetime import datetime

        # 获取当前用户的钱包地址（从多个来源）
        eth_address_header = request.headers.get('X-Eth-Address')
        eth_address_cookie = request.cookies.get('eth_address')
        eth_address_args = request.args.get('eth_address')

        # 优先使用 Args > Header > Cookie
        eth_address = eth_address_args or eth_address_header or eth_address_cookie

        # 构建日期范围（当天的开始和结束）
        start_date = datetime(year, month, day)
        end_date = datetime(year, month, day, 23, 59, 59)

        # 首先根据日期范围获取当天的所有新闻
        daily_hotspots = NewsHotspot.query.filter(
            NewsHotspot.is_active == True,
            NewsHotspot.created_at >= start_date,
            NewsHotspot.created_at <= end_date
        ).all()

        current_app.logger.info(f'日期新闻查询 - 日期: {year}-{month}-{day}, slug: {slug}')
        current_app.logger.info(f'当天找到 {len(daily_hotspots)} 个新闻')

        hotspot = None

        # 如果只有一个新闻，直接返回
        if len(daily_hotspots) == 1:
            hotspot = daily_hotspots[0]
            current_app.logger.info(f'当天只有一个新闻，直接返回: {hotspot.title}')

        # 如果有多个新闻，需要根据slug精确匹配
        elif len(daily_hotspots) > 1:
            current_app.logger.info(f'当天有多个新闻，开始slug匹配...')

            # 为每个新闻生成slug并与请求的slug比较
            for news in daily_hotspots:
                # 生成新闻的slug（与前端逻辑一致）
                import re
                news_slug = str(news.title)
                news_slug = re.sub(r'\s+', '-', news_slug)           # 空格替换为-
                news_slug = re.sub(r'[，。：？！]', '-', news_slug)    # 中文标点替换为-
                news_slug = re.sub(r'[-]+', '-', news_slug)         # 多个-合并为一个
                news_slug = re.sub(r'^-+|-+$', '', news_slug)       # 移除开头和结尾的-
                news_slug = news_slug.lower()

                # 截断slug长度
                if len(news_slug) > 50:
                    news_slug = news_slug[:50]
                    if '-' in news_slug:
                        news_slug = news_slug.rsplit('-', 1)[0]

                current_app.logger.info(f'新闻: "{news.title}" -> slug: "{news_slug}" (请求slug: "{slug}")')

                if news_slug == slug:
                    hotspot = news
                    current_app.logger.info(f'✅ 精确匹配找到: {news.title}')
                    break

        # 如果精确匹配失败，尝试模糊匹配
        if not hotspot and daily_hotspots:
            current_app.logger.warning(f'精确匹配失败，尝试模糊匹配...')
            # 将slug转换为可能的标题关键词
            title_keywords = slug.replace('-', ' ').split()
            for news in daily_hotspots:
                for keyword in title_keywords:
                    if len(keyword) > 2 and keyword.lower() in news.title.lower():
                        hotspot = news
                        current_app.logger.info(f'✅ 模糊匹配找到: {news.title} (关键词: {keyword})')
                        break
                if hotspot:
                    break

        if not hotspot:
            current_app.logger.warning(f'日期新闻详情页面 - 未找到 {year}-{month}-{day}/{slug} 的新闻')
            return render_template('404.html'), 404

        # 增加访问量（异步处理，避免影响页面加载速度）
        try:
            hotspot.increment_view_count()
            current_app.logger.info(f'新闻访问量已更新: {hotspot.title} -> {hotspot.view_count}')
        except Exception as e:
            current_app.logger.error(f'更新访问量失败: {str(e)}')

        # 获取推荐新闻（基于访问量的智能推荐）
        related_news = NewsHotspot.get_recommended_news(hotspot.id, limit=2)

        current_app.logger.info(f'日期新闻详情页面 - 成功加载新闻: {hotspot.title}')
        return render_template('news_detail.html',
                             hotspot=hotspot,
                             related_news=related_news,
                             current_user_address=eth_address)

    except Exception as e:
        current_app.logger.error(f'日期新闻详情页面 - 加载失败: {str(e)}')
        return render_template('404.html'), 404
