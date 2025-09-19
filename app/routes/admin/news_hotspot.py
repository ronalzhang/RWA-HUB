"""
新闻热点管理路由
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from app.models.news_hotspot import NewsHotspot
from app.extensions import db
from app.routes.admin.auth import api_admin_required


# 创建新闻热点管理蓝图
news_hotspot_bp = Blueprint('news_hotspot', __name__, url_prefix='/admin')
news_hotspot_api_bp = Blueprint('news_hotspot_api', __name__, url_prefix='/api/admin')


# 前端API接口 - 供首页使用
@news_hotspot_api_bp.route('/news/hotspots', methods=['GET'])
def get_public_hotspots():
    """获取公开的热点新闻列表（供首页使用）"""
    try:
        limit = request.args.get('limit', 5, type=int)
        limit = min(limit, 10)  # 最多返回10条

        hotspots = NewsHotspot.get_active_hotspots(limit=limit)

        results = []
        for hotspot in hotspots:
            results.append({
                'id': hotspot.id,
                'title': hotspot.title,
                'summary': hotspot.summary,
                'image_url': hotspot.image_url,
                'link_url': hotspot.link_url,
                'category': hotspot.category,
                'tags': hotspot.tags.split(',') if hotspot.tags else [],
                'created_at': hotspot.created_at.isoformat() if hotspot.created_at else None
            })

        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })

    except Exception as e:
        current_app.logger.error(f"获取公开热点新闻失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取新闻失败',
            'data': []
        }), 500


# 管理后台API接口
@news_hotspot_api_bp.route('/v2/news/hotspots', methods=['GET'])
@api_admin_required
def get_admin_hotspots():
    """获取热点新闻列表（管理后台）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        category = request.args.get('category', '', type=str)
        is_active = request.args.get('is_active', '', type=str)

        # 构建查询
        query = NewsHotspot.query

        if category:
            query = query.filter(NewsHotspot.category == category)

        if is_active != '':
            if is_active.lower() == 'true':
                query = query.filter(NewsHotspot.is_active == True)
            elif is_active.lower() == 'false':
                query = query.filter(NewsHotspot.is_active == False)

        # 按优先级和创建时间排序
        query = query.order_by(
            NewsHotspot.priority.desc(),
            NewsHotspot.created_at.desc()
        )

        # 分页
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        hotspots = [hotspot.to_dict() for hotspot in pagination.items]

        # 统计信息
        total_count = NewsHotspot.query.count()
        active_count = NewsHotspot.query.filter_by(is_active=True).count()
        categories = db.session.query(NewsHotspot.category).distinct().all()
        category_list = [cat[0] for cat in categories if cat[0]]

        return jsonify({
            'success': True,
            'data': {
                'hotspots': hotspots,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                },
                'stats': {
                    'total': total_count,
                    'active': active_count,
                    'categories': category_list
                }
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取热点新闻列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@news_hotspot_api_bp.route('/v2/news/hotspots', methods=['POST'])
@api_admin_required
def create_hotspot():
    """创建热点新闻"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400

        title = data.get('title', '').strip()
        if not title:
            return jsonify({
                'success': False,
                'error': '新闻标题不能为空'
            }), 400

        # 创建新的热点新闻
        hotspot = NewsHotspot(
            title=title,
            summary=data.get('summary', '').strip(),
            content=data.get('content', '').strip(),
            image_url=data.get('image_url', '').strip(),
            link_url=data.get('link_url', '').strip(),
            priority=data.get('priority', 0),
            is_active=data.get('is_active', True),
            category=data.get('category', 'general').strip(),
            tags=data.get('tags', '').strip(),
            display_order=data.get('display_order', 0)
        )

        db.session.add(hotspot)
        db.session.commit()

        current_app.logger.info(f"创建热点新闻成功: {title}")

        return jsonify({
            'success': True,
            'message': '热点新闻创建成功',
            'data': hotspot.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建热点新闻失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@news_hotspot_api_bp.route('/v2/news/hotspots/<int:hotspot_id>', methods=['PUT'])
@api_admin_required
def update_hotspot(hotspot_id):
    """更新热点新闻"""
    try:
        hotspot = NewsHotspot.query.get_or_404(hotspot_id)
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400

        title = data.get('title', '').strip()
        if not title:
            return jsonify({
                'success': False,
                'error': '新闻标题不能为空'
            }), 400

        # 更新字段
        hotspot.title = title
        hotspot.summary = data.get('summary', '').strip()
        hotspot.content = data.get('content', '').strip()
        hotspot.image_url = data.get('image_url', '').strip()
        hotspot.link_url = data.get('link_url', '').strip()
        hotspot.priority = data.get('priority', hotspot.priority)
        hotspot.is_active = data.get('is_active', hotspot.is_active)
        hotspot.category = data.get('category', hotspot.category).strip()
        hotspot.tags = data.get('tags', '').strip()
        hotspot.display_order = data.get('display_order', hotspot.display_order)
        hotspot.updated_at = datetime.utcnow()

        db.session.commit()

        current_app.logger.info(f"更新热点新闻成功: {title}")

        return jsonify({
            'success': True,
            'message': '热点新闻更新成功',
            'data': hotspot.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新热点新闻失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@news_hotspot_api_bp.route('/v2/news/hotspots/<int:hotspot_id>', methods=['DELETE'])
@api_admin_required
def delete_hotspot(hotspot_id):
    """删除热点新闻"""
    try:
        hotspot = NewsHotspot.query.get_or_404(hotspot_id)
        title = hotspot.title

        db.session.delete(hotspot)
        db.session.commit()

        current_app.logger.info(f"删除热点新闻成功: {title}")

        return jsonify({
            'success': True,
            'message': '热点新闻删除成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除热点新闻失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@news_hotspot_api_bp.route('/v2/news/hotspots/<int:hotspot_id>/toggle', methods=['POST'])
@api_admin_required
def toggle_hotspot_status(hotspot_id):
    """切换热点新闻状态"""
    try:
        hotspot = NewsHotspot.query.get_or_404(hotspot_id)

        hotspot.is_active = not hotspot.is_active
        hotspot.updated_at = datetime.utcnow()

        db.session.commit()

        status_text = '启用' if hotspot.is_active else '禁用'
        current_app.logger.info(f"{status_text}热点新闻: {hotspot.title}")

        return jsonify({
            'success': True,
            'message': f'热点新闻已{status_text}',
            'data': {
                'id': hotspot.id,
                'is_active': hotspot.is_active
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"切换热点新闻状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500