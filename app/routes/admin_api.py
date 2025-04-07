from flask import Blueprint, jsonify, request, g, current_app, session
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, text
import json
from app.utils.decorators import eth_address_required, async_task, log_activity, admin_required
from app.models.admin import (
    AdminUser, SystemConfig, CommissionSetting, DistributionLevel,
    UserReferral, CommissionRecord, AdminOperationLog, DashboardStats
)
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.user import User
from app.models.trade import Trade

# 创建蓝图
admin_v2_bp = Blueprint('admin_v2', __name__, url_prefix='/api/admin/v2')
# 为旧版API创建兼容蓝图
admin_compat_bp = Blueprint('admin_compat', __name__, url_prefix='/api/admin')

# 后台API身份验证装饰器
def admin_required(f):
    """管理员权限装饰器"""
    @eth_address_required
    def admin_check(*args, **kwargs):
        # 检查是否为管理员
        admin = AdminUser.query.filter_by(wallet_address=g.eth_address).first()
        if not admin:
            return jsonify({'error': '需要管理员权限'}), 403
        g.admin = admin
        return f(*args, **kwargs)
    admin_check.__name__ = f.__name__
    return admin_check

def permission_required(permission):
    """特定权限装饰器"""
    def decorator(f):
        @admin_required
        def permission_check(*args, **kwargs):
            admin = g.admin
            if not admin.has_permission(permission) and not admin.is_super_admin():
                return jsonify({'error': f'需要{permission}权限'}), 403
            return f(*args, **kwargs)
        permission_check.__name__ = f.__name__
        return permission_check
    return decorator

# 记录管理员操作的装饰器
def log_admin_operation(operation_type):
    """记录管理员操作的装饰器"""
    def decorator(f):
        @admin_required
        def operation_logger(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # 记录操作
            try:
                # 提取目标表和ID
                target_table = None
                target_id = None
                
                # 从URL中提取可能的资源ID
                if request.view_args:
                    for key, value in request.view_args.items():
                        if key.endswith('_id'):
                            target_table = key.replace('_id', '')
                            target_id = value
                            break
                
                # 记录操作详情
                operation_details = {
                    'method': request.method,
                    'url': request.path,
                    'args': {
                        k: v for k, v in request.args.items()
                        if k not in ['token', 'key', 'secret', 'password']
                    }
                }
                
                # 如果是POST/PUT请求，记录请求体
                if request.is_json and request.json:
                    operation_details['body'] = {
                        k: v for k, v in request.json.items()
                        if k not in ['token', 'key', 'secret', 'password']
                    }
                
                # 记录操作结果状态码
                if isinstance(result, tuple) and len(result) > 1:
                    operation_details['status_code'] = result[1]
                else:
                    operation_details['status_code'] = 200
                
                # 写入操作日志
                AdminOperationLog.log_operation(
                    admin_address=g.eth_address,
                    operation_type=operation_type,
                    target_table=target_table,
                    target_id=target_id,
                    operation_details=operation_details,
                    ip_address=request.remote_addr
                )
            except Exception as e:
                current_app.logger.error(f"记录管理员操作失败: {str(e)}")
            
            return result
        operation_logger.__name__ = f.__name__
        return operation_logger
    return decorator

# 旧版API身份验证装饰器，同时兼容新旧管理员系统
def compat_admin_required(f):
    """管理员权限装饰器(兼容旧版)"""
    @eth_address_required
    def admin_check(*args, **kwargs):
        # 先检查是否为新系统中的管理员
        admin = AdminUser.query.filter_by(wallet_address=g.eth_address).first()
        
        # 如果不是新系统中的管理员，检查是否在配置中的管理员列表
        if not admin:
            # 尝试从config.json中获取管理员配置
            try:
                import os
                import json
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        admins = config.get('admins', {})
                        if g.eth_address in admins:
                            # 设置会话标记
                            session['is_admin'] = True
                            return f(*args, **kwargs)
                        
                # 如果不在配置文件中，检查session
                if session.get('is_admin'):
                    return f(*args, **kwargs)
                    
                return jsonify({'error': '需要管理员权限'}), 403
            except Exception as e:
                current_app.logger.error(f"检查管理员权限失败: {str(e)}")
                return jsonify({'error': '权限检查失败'}), 500
        
        # 如果是新系统中的管理员
        g.admin = admin
        return f(*args, **kwargs)
        
    admin_check.__name__ = f.__name__
    return admin_check

# 仪表盘数据API
@admin_v2_bp.route('/dashboard/stats')
@admin_required
@log_admin_operation('查看仪表盘')
def get_dashboard_stats():
    """获取仪表盘概览统计数据"""
    try:
        today = datetime.utcnow().date()
        
        # 1. 检查是否有缓存的统计数据
        user_count = DashboardStats.query.filter_by(
            stat_date=today, 
            stat_type='user_count',
            stat_period='daily'
        ).first()
        
        # 如果没有今天的统计数据，触发更新
        if not user_count:
            DashboardStats.update_daily_stats()
        
        # 2. 获取统计数据
        stats = {}
        
        # 用户统计
        user_stats = DashboardStats.query.filter(
            DashboardStats.stat_date == today,
            DashboardStats.stat_type.in_(['user_count', 'new_users']),
            DashboardStats.stat_period == 'daily'
        ).all()
        
        for stat in user_stats:
            stats[stat.stat_type] = stat.stat_value
            
        # 添加本周新增用户
        week_start = today - timedelta(days=today.weekday())
        new_users_week = db.session.query(func.sum(DashboardStats.stat_value)).filter(
            DashboardStats.stat_type == 'new_users',
            DashboardStats.stat_period == 'daily',
            DashboardStats.stat_date >= week_start,
            DashboardStats.stat_date <= today
        ).scalar() or 0
        stats['new_users_week'] = new_users_week
        
        # 资产统计
        asset_stats = DashboardStats.query.filter(
            DashboardStats.stat_date == today,
            DashboardStats.stat_type.in_(['asset_count', 'asset_value']),
            DashboardStats.stat_period == 'daily'
        ).all()
        
        for stat in asset_stats:
            stats[stat.stat_type] = stat.stat_value
            
        # 交易统计
        trade_stats = DashboardStats.query.filter(
            DashboardStats.stat_date == today,
            DashboardStats.stat_type.in_(['trade_count', 'trade_volume']),
            DashboardStats.stat_period == 'daily'
        ).all()
        
        for stat in trade_stats:
            stats[stat.stat_type] = stat.stat_value
            
        # 添加一些友好的键名，兼容旧的API格式
        response = {
            'total_users': stats.get('user_count', 0),
            'new_users_today': stats.get('new_users', 0),
            'new_users_week': stats.get('new_users_week', 0),
            'total_assets': stats.get('asset_count', 0),
            'total_asset_value': stats.get('asset_value', 0),
            'total_trades': stats.get('trade_count', 0),
            'total_trade_volume': stats.get('trade_volume', 0)
        }
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"获取仪表盘统计数据失败: {str(e)}")
        return jsonify({'error': '获取统计数据失败', 'message': str(e)}), 500

@admin_v2_bp.route('/dashboard/trends')
@admin_required
def get_dashboard_trends():
    """获取仪表盘趋势数据"""
    try:
        days = request.args.get('days', 30, type=int)
        if days > 365:
            days = 365  # 限制最大天数
            
        # 获取用户增长趋势
        user_trend = DashboardStats.get_trend_data('new_users', days)
        
        # 获取交易量趋势
        trade_trend = DashboardStats.get_trend_data('trade_volume', days)
        
        # 获取资产价值趋势
        value_trend = DashboardStats.get_trend_data('asset_value', days)
        
        return jsonify({
            'user_growth': user_trend,
            'trade_volume': trade_trend,
            'asset_value': value_trend
        })
        
    except Exception as e:
        current_app.logger.error(f"获取仪表盘趋势数据失败: {str(e)}")
        return jsonify({'error': '获取趋势数据失败', 'message': str(e)}), 500

@admin_v2_bp.route('/user-growth-stats')
@admin_required
def get_user_growth_stats():
    """获取用户统计数据，包括增长趋势"""
    try:
        period = request.args.get('period', 'weekly')
        days = 7
        
        if period == 'monthly':
            days = 30
        elif period == 'yearly':
            days = 365
        elif period == 'daily':
            days = 1
            
        # 获取用户增长趋势
        user_trend = DashboardStats.get_trend_data('new_users', days)
        
        # 获取用户地理分布 (假数据，实际应从用户IP或注册信息中获取)
        regions = [
            {'name': '中国', 'value': 60},
            {'name': '美国', 'value': 20},
            {'name': '欧洲', 'value': 15},
            {'name': '其他', 'value': 5}
        ]
        
        return jsonify({
            'trend': [
                {'date': user_trend['labels'][i], 'count': user_trend['values'][i]}
                for i in range(len(user_trend['labels']))
            ],
            'regions': regions
        })
        
    except Exception as e:
        current_app.logger.error(f"获取用户统计数据失败: {str(e)}")
        return jsonify({'error': '获取用户统计数据失败', 'message': str(e)}), 500

@admin_v2_bp.route('/asset-type-stats')
@admin_required
def get_asset_type_stats():
    """获取资产类型分布统计"""
    try:
        current_app.logger.info('获取资产类型分布统计...')
        
        # 查询资产类型分布
        distribution = db.session.query(
            Asset.asset_type.label('type'),
            func.count(Asset.id).label('count'),
            func.sum(Asset.total_value).label('value')
        ).group_by(Asset.asset_type).all()
        
        # 类型名称映射
        type_names = {
            10: '不动产',
            20: '商业地产',
            30: '工业地产',
            40: '土地资产',
            50: '证券资产',
            60: '艺术品',
            70: '收藏品',
            99: '其他'
        }
        
        # 构建响应数据
        result = []
        for type_id, count, value in distribution:
            type_name = type_names.get(type_id, f'未知类型({type_id})')
            result.append({
                'type': type_id,
                'name': type_name,
                'count': count,
                'value': float(value) if value else 0
            })
            
        return jsonify({
            'distribution': result
        })
        
    except Exception as e:
        current_app.logger.error(f"获取资产类型分布统计失败: {str(e)}")
        return jsonify({'error': '获取资产类型统计失败', 'message': str(e)}), 500

@admin_v2_bp.route('/dashboard/refresh', methods=['POST'])
@admin_required
@permission_required('管理仪表盘')
@log_admin_operation('刷新仪表盘')
def refresh_dashboard_stats():
    """手动刷新仪表盘统计数据"""
    try:
        # 使用异步任务更新统计
        @async_task
        def update_stats():
            DashboardStats.update_daily_stats()
            current_app.logger.info("仪表盘统计数据已更新")
            
        update_stats()
        
        return jsonify({
            'message': '已触发仪表盘数据更新',
            'success': True
        })
        
    except Exception as e:
        current_app.logger.error(f"刷新仪表盘统计数据失败: {str(e)}")
        return jsonify({'error': '刷新仪表盘统计数据失败', 'message': str(e)}), 500

# 资产管理API
@admin_v2_bp.route('/assets')
@admin_required
def list_assets():
    """获取资产列表，支持分页和筛选"""
    try:
        # 获取请求参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status')
        asset_type = request.args.get('type')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 构建查询
        query = Asset.query
        
        # 过滤条件
        if status:
            try:
                status_value = int(status)
                query = query.filter(Asset.status == status_value)
            except ValueError:
                pass
        
        if asset_type:
            try:
                type_value = int(asset_type)
                query = query.filter(Asset.asset_type == type_value)
            except ValueError:
                pass
        
        # 搜索条件
        if search:
            query = query.filter(
                db.or_(
                    Asset.name.ilike(f'%{search}%'),
                    Asset.description.ilike(f'%{search}%'),
                    Asset.location.ilike(f'%{search}%'),
                    Asset.token_symbol.ilike(f'%{search}%')
                )
            )
        
        # 排序
        if sort_by == 'created_at':
            if sort_order == 'desc':
                query = query.order_by(Asset.created_at.desc())
            else:
                query = query.order_by(Asset.created_at.asc())
        elif sort_by == 'price':
            if sort_order == 'desc':
                query = query.order_by(Asset.token_price.desc())
            else:
                query = query.order_by(Asset.token_price.asc())
        elif sort_by == 'value':
            if sort_order == 'desc':
                query = query.order_by(Asset.total_value.desc())
            else:
                query = query.order_by(Asset.total_value.asc())
        elif sort_by == 'name':
            if sort_order == 'desc':
                query = query.order_by(Asset.name.desc())
            else:
                query = query.order_by(Asset.name.asc())
        
        # 总数
        total = query.count()
        
        # 分页
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        # 状态文本映射
        status_map = {
            1: '待审核',
            2: '已通过',
            3: '已拒绝',
            4: '已删除'
        }
        
        # 类型文本映射
        type_map = {
            10: '不动产',
            20: '商业地产',
            30: '工业地产',
            40: '土地资产',
            50: '证券资产',
            60: '艺术品',
            70: '收藏品',
            99: '其他'
        }
        
        # 转换为字典
        assets = []
        for asset in pagination.items:
            asset_dict = asset.to_dict()
            asset_dict['status_text'] = status_map.get(asset.status, '未知')
            asset_dict['type_text'] = type_map.get(asset.asset_type, '未知')
            
            # 添加交易统计
            asset_dict['trades_count'] = Trade.query.filter_by(asset_id=asset.id).count()
            
            # 首图
            if asset.images and len(asset.images) > 0:
                asset_dict['cover_image'] = asset.images[0]
            else:
                asset_dict['cover_image'] = None
                
            assets.append(asset_dict)
        
        return jsonify({
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': pagination.pages,
            'assets': assets
        })
        
    except Exception as e:
        current_app.logger.error(f"获取资产列表失败: {str(e)}")
        return jsonify({'error': '获取资产列表失败', 'message': str(e)}), 500

@admin_v2_bp.route('/assets/<int:asset_id>')
@admin_required
def get_asset(asset_id):
    """获取资产详情"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 转换为字典并添加额外信息
        asset_dict = asset.to_dict()
        
        # 添加状态文本
        status_map = {
            1: '待审核',
            2: '已通过',
            3: '已拒绝',
            4: '已删除'
        }
        asset_dict['status_text'] = status_map.get(asset.status, '未知')
        
        # 添加类型文本
        type_map = {
            10: '不动产',
            20: '商业地产',
            30: '工业地产',
            40: '土地资产',
            50: '证券资产',
            60: '艺术品',
            70: '收藏品',
            99: '其他'
        }
        asset_dict['type_text'] = type_map.get(asset.asset_type, '未知')
        
        # 添加交易统计
        asset_dict['trades_count'] = Trade.query.filter_by(asset_id=asset.id).count()
        
        # 获取最近几笔交易
        recent_trades = Trade.query.filter_by(asset_id=asset.id) \
            .order_by(Trade.created_at.desc()) \
            .limit(5).all()
        asset_dict['recent_trades'] = [trade.to_dict() for trade in recent_trades]
        
        return jsonify(asset_dict)
        
    except Exception as e:
        current_app.logger.error(f"获取资产详情失败: {str(e)}")
        return jsonify({'error': '获取资产详情失败', 'message': str(e)}), 500

@admin_v2_bp.route('/assets/<int:asset_id>/approve', methods=['POST'])
@admin_required
@permission_required('审核资产')
@log_admin_operation('审核资产')
def approve_asset(asset_id):
    """审核通过资产"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        if asset.status != AssetStatus.PENDING.value:
            return jsonify({'error': '只能审核待审核状态的资产'}), 400
        
        # 更新状态
        asset.status = AssetStatus.APPROVED.value
        db.session.commit()
        
        return jsonify({
            'message': '资产审核通过成功',
            'asset_id': asset_id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"审核资产失败: {str(e)}")
        return jsonify({'error': '审核资产失败', 'message': str(e)}), 500

@admin_v2_bp.route('/assets/<int:asset_id>/reject', methods=['POST'])
@admin_required
@permission_required('审核资产')
@log_admin_operation('拒绝资产')
def reject_asset(asset_id):
    """拒绝资产"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        if asset.status != AssetStatus.PENDING.value:
            return jsonify({'error': '只能拒绝待审核状态的资产'}), 400
        
        # 获取拒绝原因
        data = request.get_json()
        if not data or not data.get('reason'):
            return jsonify({'error': '请提供拒绝原因'}), 400
        
        # 更新状态
        asset.status = AssetStatus.REJECTED.value
        asset.reject_reason = data['reason']
        db.session.commit()
        
        return jsonify({
            'message': '资产拒绝成功',
            'asset_id': asset_id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"拒绝资产失败: {str(e)}")
        return jsonify({'error': '拒绝资产失败', 'message': str(e)}), 500

@admin_v2_bp.route('/assets/pending')
@admin_required
def get_pending_assets():
    """获取待审核资产列表"""
    try:
        # 获取请求参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        
        # 查询待审核资产
        query = Asset.query.filter(Asset.status == AssetStatus.PENDING.value) \
            .order_by(Asset.created_at.desc())
        
        # 总数
        total = query.count()
        
        # 分页
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        # 转换为字典
        assets = [asset.to_dict() for asset in pagination.items]
        
        return jsonify({
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': pagination.pages,
            'assets': assets
        })
        
    except Exception as e:
        current_app.logger.error(f"获取待审核资产列表失败: {str(e)}")
        return jsonify({'error': '获取待审核资产列表失败', 'message': str(e)}), 500

@admin_v2_bp.route('/assets/batch-approve', methods=['POST'])
@admin_required
@permission_required('审核资产')
@log_admin_operation('批量审核资产')
def batch_approve_assets():
    """批量审核通过资产"""
    try:
        data = request.get_json()
        if not data or not data.get('asset_ids'):
            return jsonify({'error': '请提供资产ID列表'}), 400
        
        asset_ids = data['asset_ids']
        
        # 查询资产
        assets = Asset.query.filter(
            Asset.id.in_(asset_ids),
            Asset.status == AssetStatus.PENDING.value
        ).all()
        
        # 更新状态
        approved_ids = []
        for asset in assets:
            asset.status = AssetStatus.APPROVED.value
            approved_ids.append(asset.id)
        
        db.session.commit()
        
        return jsonify({
            'message': f'已批量审核通过{len(approved_ids)}个资产',
            'approved_ids': approved_ids
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量审核资产失败: {str(e)}")
        return jsonify({'error': '批量审核资产失败', 'message': str(e)}), 500

@admin_v2_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """获取用户列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        search = request.args.get('search', '')
        user_type = request.args.get('user_type', '')
        registration_time = request.args.get('registration_time', '')
        
        # 构建查询
        from app.models.user import User
        from sqlalchemy import or_, func
        from datetime import datetime, timedelta
        
        query = User.query
        
        # 搜索条件
        if search:
            query = query.filter(or_(
                User.wallet_address.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            ))
        
        # 用户类型过滤
        if user_type == 'verified':
            query = query.filter(User.is_verified == True)
        elif user_type == 'distributor':
            query = query.filter(User.is_distributor == True)
        elif user_type == 'normal':
            query = query.filter(User.is_verified == False, User.is_distributor == False)
        
        # 注册时间过滤
        today = datetime.utcnow().date()
        if registration_time == 'today':
            query = query.filter(func.date(User.created_at) == today)
        elif registration_time == 'week':
            week_start = today - timedelta(days=today.weekday())
            query = query.filter(func.date(User.created_at) >= week_start)
        elif registration_time == 'month':
            month_start = today.replace(day=1)
            query = query.filter(func.date(User.created_at) >= month_start)
        elif registration_time == 'quarter':
            quarter_start = today - timedelta(days=90)
            query = query.filter(func.date(User.created_at) >= quarter_start)
        elif registration_time == 'year':
            year_start = today.replace(month=1, day=1)
            query = query.filter(func.date(User.created_at) >= year_start)
        
        # 计算总数和页数
        total = query.count()
        total_pages = (total + page_size - 1) // page_size
        
        # 获取分页数据
        users = query.order_by(User.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()
        
        # 格式化响应数据
        user_list = []
        for user in users:
            # 获取交易次数
            from app.models.trade import Trade
            trade_count = Trade.query.filter(or_(
                Trade.buyer_address == user.wallet_address,
                Trade.seller_address == user.wallet_address
            )).count()
            
            # 获取持有资产数
            from app.models.asset import Asset
            assets_count = Asset.query.filter_by(creator_address=user.wallet_address).count()
            
            user_list.append({
                'wallet_address': user.wallet_address,
                'username': user.username,
                'email': user.email,
                'is_verified': bool(user.is_verified),
                'is_distributor': bool(getattr(user, 'is_distributor', False)),
                'is_blocked': bool(getattr(user, 'is_blocked', False)),
                'created_at': user.created_at.isoformat(),
                'trade_count': trade_count,
                'assets_count': assets_count,
                'referrer': getattr(user, 'referrer', None)
            })
        
        return jsonify({
            'users': user_list,
            'total': total,
            'total_pages': total_pages,
            'page': page,
            'page_size': page_size
        })
    
    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_v2_bp.route('/user-stats', methods=['GET'])
@admin_required
def get_user_stats():
    """获取用户统计数据"""
    try:
        from app.models.user import User
        from sqlalchemy import func
        from datetime import datetime
        
        # 总用户数
        total_users = User.query.count()
        
        # 已认证用户数
        verified_users = User.query.filter_by(is_verified=True).count()
        
        # 分销商数量
        distributors = User.query.filter(getattr(User, 'is_distributor', False) == True).count()
        
        # 今日新增用户
        today = datetime.utcnow().date()
        new_today = User.query.filter(func.date(User.created_at) == today).count()
        
        return jsonify({
            'totalUsers': total_users,
            'verifiedUsers': verified_users,
            'distributors': distributors,
            'newToday': new_today
        })
    
    except Exception as e:
        current_app.logger.error(f"获取用户统计失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_v2_bp.route('/users/<address>/verify', methods=['POST'])
@admin_required
def verify_user(address):
    """认证用户"""
    try:
        from app.models.user import User
        from app.models.admin import AdminOperationLog
        
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        user.is_verified = True
        
        # 记录管理员操作
        admin_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address') or session.get('eth_address')
        log = AdminOperationLog(
            admin_address=admin_address,
            operation_type='verify_user',
            target_table='users',
            operation_details=json.dumps({
                'user_address': address,
                'action': 'verify'
            }),
            ip_address=request.remote_addr
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '用户已认证'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"认证用户失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_v2_bp.route('/users/<address>/set-distributor', methods=['POST'])
@admin_required
def set_distributor(address):
    """设置用户为分销商"""
    try:
        from app.models.user import User
        from app.models.admin import AdminOperationLog
        
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        # 检查is_distributor属性是否存在
        if not hasattr(user, 'is_distributor'):
            return jsonify({'error': '分销商功能尚未开启'}), 400
        
        user.is_distributor = True
        
        # 记录管理员操作
        admin_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address') or session.get('eth_address')
        log = AdminOperationLog(
            admin_address=admin_address,
            operation_type='set_distributor',
            target_table='users',
            operation_details=json.dumps({
                'user_address': address,
                'action': 'set_distributor'
            }),
            ip_address=request.remote_addr
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '用户已设置为分销商'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"设置分销商失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_v2_bp.route('/users/<address>/block', methods=['POST'])
@admin_required
def block_user(address):
    """冻结用户"""
    try:
        from app.models.user import User
        from app.models.admin import AdminOperationLog
        
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        # 检查is_blocked属性是否存在
        if not hasattr(user, 'is_blocked'):
            return jsonify({'error': '用户冻结功能尚未开启'}), 400
        
        user.is_blocked = True
        
        # 记录管理员操作
        admin_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address') or session.get('eth_address')
        log = AdminOperationLog(
            admin_address=admin_address,
            operation_type='block_user',
            target_table='users',
            operation_details=json.dumps({
                'user_address': address,
                'action': 'block'
            }),
            ip_address=request.remote_addr
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '用户已冻结'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"冻结用户失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_v2_bp.route('/users/<address>/unblock', methods=['POST'])
@admin_required
def unblock_user(address):
    """解冻用户"""
    try:
        from app.models.user import User
        from app.models.admin import AdminOperationLog
        
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        # 检查is_blocked属性是否存在
        if not hasattr(user, 'is_blocked'):
            return jsonify({'error': '用户冻结功能尚未开启'}), 400
        
        user.is_blocked = False
        
        # 记录管理员操作
        admin_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address') or session.get('eth_address')
        log = AdminOperationLog(
            admin_address=admin_address,
            operation_type='unblock_user',
            target_table='users',
            operation_details=json.dumps({
                'user_address': address,
                'action': 'unblock'
            }),
            ip_address=request.remote_addr
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '用户已解冻'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"解冻用户失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_v2_bp.route('/users/export', methods=['GET'])
@admin_required
def export_users():
    """导出用户数据"""
    try:
        import csv
        import io
        from app.models.user import User
        from sqlalchemy import or_
        from datetime import datetime, timedelta
        
        # 解析查询参数
        search = request.args.get('search', '')
        user_type = request.args.get('user_type', '')
        registration_time = request.args.get('registration_time', '')
        
        # 构建查询
        query = User.query
        
        # 搜索条件
        if search:
            query = query.filter(or_(
                User.wallet_address.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            ))
        
        # 用户类型过滤
        if user_type == 'verified':
            query = query.filter(User.is_verified == True)
        elif user_type == 'distributor':
            query = query.filter(getattr(User, 'is_distributor', False) == True)
        elif user_type == 'normal':
            query = query.filter(User.is_verified == False, getattr(User, 'is_distributor', False) == False)
        
        # 注册时间过滤
        today = datetime.utcnow().date()
        if registration_time == 'today':
            query = query.filter(func.date(User.created_at) == today)
        elif registration_time == 'week':
            week_start = today - timedelta(days=today.weekday())
            query = query.filter(func.date(User.created_at) >= week_start)
        elif registration_time == 'month':
            month_start = today.replace(day=1)
            query = query.filter(func.date(User.created_at) >= month_start)
        elif registration_time == 'quarter':
            quarter_start = today - timedelta(days=90)
            query = query.filter(func.date(User.created_at) >= quarter_start)
        elif registration_time == 'year':
            year_start = today.replace(month=1, day=1)
            query = query.filter(func.date(User.created_at) >= year_start)
        
        # 获取所有用户
        users = query.order_by(User.created_at.desc()).all()
        
        # 创建CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入CSV头
        writer.writerow(['钱包地址', '用户名', '邮箱', '注册时间', '是否认证', '是否分销商', '是否冻结'])
        
        # 写入用户数据
        for user in users:
            writer.writerow([
                user.wallet_address,
                user.username or '',
                user.email or '',
                user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '是' if getattr(user, 'is_verified', False) else '否',
                '是' if getattr(user, 'is_distributor', False) else '否',
                '是' if getattr(user, 'is_blocked', False) else '否'
            ])
        
        # 设置响应头
        output.seek(0)
        response = current_app.response_class(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=users_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
            }
        )
        
        return response
    
    except Exception as e:
        current_app.logger.error(f"导出用户数据失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# 注册蓝图
def register_admin_v2_blueprint(app):
    app.register_blueprint(admin_v2_bp)
    app.register_blueprint(admin_compat_bp)
    current_app.logger.info("管理员API v2已注册")

# 添加兼容旧版API的路由
@admin_compat_bp.route('/stats')
@compat_admin_required
def get_stats_compat():
    """兼容旧版API的统计数据接口"""
    try:
        # 直接准备数据而不是调用函数(避免重定向)
        today = datetime.utcnow().date()
        
        # 1. 检查是否有缓存的统计数据
        user_count = DashboardStats.query.filter_by(
            stat_date=today, 
            stat_type='user_count',
            stat_period='daily'
        ).first()
        
        # 如果没有今天的统计数据，触发更新
        if not user_count:
            # 先尝试使用更精确的直接从数据库更新方法
            if not DashboardStats.update_stats_from_db():
                # 如果直接更新失败，使用默认方法
                DashboardStats.update_daily_stats()
        
        # 2. 获取统计数据
        stats = {}
        
        # 用户统计
        user_stats = DashboardStats.query.filter(
            DashboardStats.stat_date == today,
            DashboardStats.stat_type.in_(['user_count', 'new_users']),
            DashboardStats.stat_period == 'daily'
        ).all()
        
        for stat in user_stats:
            stats[stat.stat_type] = stat.stat_value
            
        # 添加本周新增用户
        week_start = today - timedelta(days=today.weekday())
        new_users_week = db.session.query(func.sum(DashboardStats.stat_value)).filter(
            DashboardStats.stat_type == 'new_users',
            DashboardStats.stat_period == 'daily',
            DashboardStats.stat_date >= week_start,
            DashboardStats.stat_date <= today
        ).scalar() or 0
        stats['new_users_week'] = new_users_week
        
        # 资产统计
        asset_stats = DashboardStats.query.filter(
            DashboardStats.stat_date == today,
            DashboardStats.stat_type.in_(['asset_count', 'asset_value']),
            DashboardStats.stat_period == 'daily'
        ).all()
        
        for stat in asset_stats:
            stats[stat.stat_type] = stat.stat_value
            
        # 交易统计
        trade_stats = DashboardStats.query.filter(
            DashboardStats.stat_date == today,
            DashboardStats.stat_type.in_(['trade_count', 'trade_volume']),
            DashboardStats.stat_period == 'daily'
        ).all()
        
        for stat in trade_stats:
            stats[stat.stat_type] = stat.stat_value
            
        # 添加一些友好的键名，兼容旧的API格式
        response = {
            'total_users': stats.get('user_count', 0),
            'new_users_today': stats.get('new_users', 0),
            'new_users_week': stats.get('new_users_week', 0),
            'total_assets': stats.get('asset_count', 0),
            'total_asset_value': stats.get('asset_value', 0),
            'total_trades': stats.get('trade_count', 0),
            'total_trade_volume': stats.get('trade_volume', 0)
        }
        
        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"获取仪表盘统计数据失败: {str(e)}")
        return jsonify({'error': '获取统计数据失败', 'message': str(e)}), 500

@admin_compat_bp.route('/asset-type-stats')
@compat_admin_required
def get_asset_type_stats_compat():
    """兼容旧版API的资产类型分布接口"""
    try:
        current_app.logger.info('获取资产类型分布统计...')
        
        # 查询资产类型分布
        distribution = db.session.query(
            Asset.asset_type.label('type'),
            func.count(Asset.id).label('count'),
            func.sum(Asset.total_value).label('value')
        ).group_by(Asset.asset_type).all()
        
        # 类型名称映射
        type_names = {
            10: '不动产',
            20: '商业地产',
            30: '工业地产',
            40: '土地资产',
            50: '证券资产',
            60: '艺术品',
            70: '收藏品',
            99: '其他'
        }
        
        # 构建响应数据
        result = []
        for type_id, count, value in distribution:
            type_name = type_names.get(type_id, f'未知类型({type_id})')
            result.append({
                'type': type_id,
                'name': type_name,
                'count': count,
                'value': float(value) if value else 0
            })
            
        return jsonify({
            'distribution': result
        })
    except Exception as e:
        current_app.logger.error(f"获取资产类型分布统计失败: {str(e)}")
        return jsonify({'error': '获取资产类型统计失败', 'message': str(e)}), 500

@admin_compat_bp.route('/user-stats')
@compat_admin_required
def get_user_stats_compat():
    """兼容旧版API的用户统计接口"""
    try:
        period = request.args.get('period', 'weekly')
        days = 7
        
        if period == 'monthly':
            days = 30
        elif period == 'yearly':
            days = 365
        elif period == 'daily':
            days = 1
        
        # 获取用户增长趋势
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # 查询每日新增用户
        daily_new_users = DashboardStats.query.filter(
            DashboardStats.stat_type == 'new_users',
            DashboardStats.stat_period == 'daily',
            DashboardStats.stat_date >= start_date,
            DashboardStats.stat_date <= end_date
        ).order_by(DashboardStats.stat_date).all()
        
        # 构造趋势数据
        trend = []
        for stat in daily_new_users:
            trend.append({
                'date': stat.stat_date.strftime('%Y-%m-%d'),
                'count': stat.stat_value
            })
            
        # 获取用户地理分布 (假数据，实际应从用户IP或注册信息中获取)
        regions = [
            {'name': '中国', 'value': 60},
            {'name': '美国', 'value': 20},
            {'name': '欧洲', 'value': 15},
            {'name': '其他', 'value': 5}
        ]
        
        return jsonify({
            'trend': trend,
            'regions': regions
        })
    except Exception as e:
        current_app.logger.error(f"获取用户统计数据失败: {str(e)}")
        return jsonify({'error': '获取用户统计数据失败', 'message': str(e)}), 500

# 分销等级相关API
@admin_v2_bp.route('/distribution-levels', methods=['GET'])
@admin_required
def get_distribution_levels():
    """获取分销等级列表"""
    try:
        levels = DistributionLevel.query.order_by(DistributionLevel.level).all()
        return jsonify({
            'success': True,
            'data': [level.to_dict() for level in levels]
        })
    except Exception as e:
        current_app.logger.error(f"获取分销等级失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取分销等级失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/distribution-levels', methods=['POST'])
@admin_required
@permission_required('管理分销')
@log_admin_operation('创建分销等级')
def create_distribution_level():
    """创建分销等级"""
    try:
        data = request.json
        
        # 验证数据
        if 'level' not in data or 'commission_rate' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数：level 或 commission_rate'
            }), 400
        
        # 检查等级是否已存在
        if DistributionLevel.query.filter_by(level=data['level']).first():
            return jsonify({
                'success': False,
                'error': f'等级 {data["level"]} 已存在'
            }), 400
        
        # 创建分销等级
        level = DistributionLevel(
            level=data['level'],
            commission_rate=data['commission_rate'],
            description=data.get('description', ''),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(level)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '分销等级创建成功',
            'data': level.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建分销等级失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"创建分销等级失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/distribution-levels/<int:level_id>', methods=['PUT'])
@admin_required
@permission_required('管理分销')
@log_admin_operation('更新分销等级')
def update_distribution_level(level_id):
    """更新分销等级"""
    try:
        level = DistributionLevel.query.get(level_id)
        if not level:
            return jsonify({
                'success': False,
                'error': f'未找到ID为{level_id}的分销等级'
            }), 404
        
        data = request.json
        
        # 检查是否有其他记录使用相同的等级值
        if 'level' in data and data['level'] != level.level:
            if DistributionLevel.query.filter_by(level=data['level']).first():
                return jsonify({
                    'success': False,
                    'error': f'等级 {data["level"]} 已存在'
                }), 400
            level.level = data['level']
        
        # 更新其他字段
        if 'commission_rate' in data:
            level.commission_rate = data['commission_rate']
        if 'description' in data:
            level.description = data['description']
        if 'is_active' in data:
            level.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '分销等级更新成功',
            'data': level.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新分销等级失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"更新分销等级失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/distribution-levels/<int:level_id>', methods=['DELETE'])
@admin_required
@permission_required('管理分销')
@log_admin_operation('删除分销等级')
def delete_distribution_level(level_id):
    """删除分销等级"""
    try:
        level = DistributionLevel.query.get(level_id)
        if not level:
            return jsonify({
                'success': False,
                'error': f'未找到ID为{level_id}的分销等级'
            }), 404
        
        # 检查是否有用户推荐关系使用此等级
        if UserReferral.query.filter_by(referral_level=level.level).first():
            return jsonify({
                'success': False,
                'error': f'无法删除该等级，存在用户推荐关系使用了此等级'
            }), 400
        
        db.session.delete(level)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '分销等级删除成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除分销等级失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"删除分销等级失败: {str(e)}"
        }), 500

# 用户推荐关系相关API
@admin_v2_bp.route('/user-referrals', methods=['GET'])
@admin_required
def get_user_referrals():
    """获取用户推荐关系列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 筛选条件
        filters = []
        if request.args.get('user_address'):
            filters.append(UserReferral.user_address == request.args.get('user_address'))
        if request.args.get('referrer_address'):
            filters.append(UserReferral.referrer_address == request.args.get('referrer_address'))
        if request.args.get('referral_level'):
            filters.append(UserReferral.referral_level == request.args.get('referral_level', type=int))
        
        # 查询记录
        query = UserReferral.query.filter(*filters).order_by(UserReferral.joined_at.desc())
        pagination = query.paginate(page=page, per_page=per_page)
        referrals = pagination.items
        
        return jsonify({
            'success': True,
            'data': [referral.to_dict() for referral in referrals],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取用户推荐关系失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取用户推荐关系失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/user-referrals', methods=['POST'])
@admin_required
@permission_required('管理分销')
@log_admin_operation('创建用户推荐关系')
def create_user_referral():
    """创建用户推荐关系"""
    try:
        data = request.json
        
        # 验证数据
        if 'user_address' not in data or 'referrer_address' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数：user_address 或 referrer_address'
            }), 400
        
        # 检查用户地址和推荐人地址是否相同
        if data['user_address'] == data['referrer_address']:
            return jsonify({
                'success': False,
                'error': '用户地址不能与推荐人地址相同'
            }), 400
        
        # 检查该用户是否已有推荐关系
        if UserReferral.query.filter_by(user_address=data['user_address']).first():
            return jsonify({
                'success': False,
                'error': f'用户 {data["user_address"]} 已有推荐关系'
            }), 400
        
        # 检查分销等级是否有效
        referral_level = data.get('referral_level', 1)
        if not DistributionLevel.query.filter_by(level=referral_level).first():
            return jsonify({
                'success': False,
                'error': f'分销等级 {referral_level} 不存在'
            }), 400
        
        # 创建推荐关系
        referral = UserReferral(
            user_address=data['user_address'],
            referrer_address=data['referrer_address'],
            referral_level=referral_level,
            referral_code=data.get('referral_code')
        )
        
        db.session.add(referral)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户推荐关系创建成功',
            'data': referral.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建用户推荐关系失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"创建用户推荐关系失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/user-referrals/<int:referral_id>', methods=['PUT'])
@admin_required
@permission_required('管理分销')
@log_admin_operation('更新用户推荐关系')
def update_user_referral(referral_id):
    """更新用户推荐关系"""
    try:
        referral = UserReferral.query.get(referral_id)
        if not referral:
            return jsonify({
                'success': False,
                'error': f'未找到ID为{referral_id}的推荐关系'
            }), 404
        
        data = request.json
        
        # 更新字段
        if 'referrer_address' in data:
            # 检查用户地址和推荐人地址是否相同
            if data['referrer_address'] == referral.user_address:
                return jsonify({
                    'success': False,
                    'error': '用户地址不能与推荐人地址相同'
                }), 400
            referral.referrer_address = data['referrer_address']
        
        if 'referral_level' in data:
            # 检查分销等级是否有效
            if not DistributionLevel.query.filter_by(level=data['referral_level']).first():
                return jsonify({
                    'success': False,
                    'error': f'分销等级 {data["referral_level"]} 不存在'
                }), 400
            referral.referral_level = data['referral_level']
        
        if 'referral_code' in data:
            referral.referral_code = data['referral_code']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户推荐关系更新成功',
            'data': referral.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新用户推荐关系失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"更新用户推荐关系失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/user-referrals/<int:referral_id>', methods=['DELETE'])
@admin_required
@permission_required('管理分销')
@log_admin_operation('删除用户推荐关系')
def delete_user_referral(referral_id):
    """删除用户推荐关系"""
    try:
        referral = UserReferral.query.get(referral_id)
        if not referral:
            return jsonify({
                'success': False,
                'error': f'未找到ID为{referral_id}的推荐关系'
            }), 404
        
        db.session.delete(referral)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户推荐关系删除成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除用户推荐关系失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"删除用户推荐关系失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/user-referrals/network/<address>', methods=['GET'])
@admin_required
def get_user_referral_network(address):
    """获取用户推荐网络"""
    try:
        # 查找用户直接推荐的用户
        direct_referrals = UserReferral.query.filter_by(referrer_address=address).all()
        
        result = {
            'address': address,
            'direct_count': len(direct_referrals),
            'direct_referrals': [ref.to_dict() for ref in direct_referrals],
            'total_network': 0,
            'levels': {}
        }
        
        # 计算总网络规模和各等级人数
        result['total_network'] = len(direct_referrals)
        
        # 统计每个等级的人数
        level_counts = {}
        for ref in direct_referrals:
            level = ref.referral_level
            level_counts[level] = level_counts.get(level, 0) + 1
        
        for level, count in level_counts.items():
            result['levels'][f'level_{level}'] = count
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        current_app.logger.error(f"获取用户推荐网络失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取用户推荐网络失败: {str(e)}"
        }), 500

# 佣金设置相关API
@admin_v2_bp.route('/commission-settings', methods=['GET'])
@admin_required
def get_commission_settings():
    """获取所有佣金设置"""
    try:
        # 获取全局佣金设置（asset_type_id为NULL）
        global_settings = CommissionSetting.query.filter_by(asset_type_id=None).all()
        
        # 获取资产类型特定设置
        type_settings = CommissionSetting.query.filter(CommissionSetting.asset_type_id.isnot(None)).all()
        
        # 构建返回数据
        result = {
            'global': [setting.to_dict() for setting in global_settings],
            'asset_types': [setting.to_dict() for setting in type_settings]
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        current_app.logger.error(f"获取佣金设置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取佣金设置失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/commission-settings', methods=['POST'])
@admin_required
@permission_required('管理佣金')
@log_admin_operation('创建佣金设置')
def create_commission_setting():
    """创建佣金设置"""
    try:
        data = request.json
        
        # 验证数据
        if 'commission_rate' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数：commission_rate'
            }), 400
        
        # 创建佣金设置记录
        setting = CommissionSetting(
            asset_type_id=data.get('asset_type_id'),
            commission_rate=data.get('commission_rate'),
            min_amount=data.get('min_amount'),
            max_amount=data.get('max_amount'),
            is_active=data.get('is_active', True),
            created_by=g.eth_address
        )
        
        db.session.add(setting)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '佣金设置创建成功',
            'data': setting.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建佣金设置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"创建佣金设置失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/commission-settings/<int:setting_id>', methods=['PUT'])
@admin_required
@permission_required('管理佣金')
@log_admin_operation('更新佣金设置')
def update_commission_setting(setting_id):
    """更新佣金设置"""
    try:
        setting = CommissionSetting.query.get(setting_id)
        if not setting:
            return jsonify({
                'success': False,
                'error': f'未找到ID为{setting_id}的佣金设置'
            }), 404
        
        data = request.json
        
        # 更新字段
        if 'asset_type_id' in data:
            setting.asset_type_id = data['asset_type_id']
        if 'commission_rate' in data:
            setting.commission_rate = data['commission_rate']
        if 'min_amount' in data:
            setting.min_amount = data['min_amount']
        if 'max_amount' in data:
            setting.max_amount = data['max_amount']
        if 'is_active' in data:
            setting.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '佣金设置更新成功',
            'data': setting.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新佣金设置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"更新佣金设置失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/commission-settings/<int:setting_id>', methods=['DELETE'])
@admin_required
@permission_required('管理佣金')
@log_admin_operation('删除佣金设置')
def delete_commission_setting(setting_id):
    """删除佣金设置"""
    try:
        setting = CommissionSetting.query.get(setting_id)
        if not setting:
            return jsonify({
                'success': False,
                'error': f'未找到ID为{setting_id}的佣金设置'
            }), 404
        
        db.session.delete(setting)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '佣金设置删除成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除佣金设置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"删除佣金设置失败: {str(e)}"
        }), 500

# 佣金记录相关API
@admin_v2_bp.route('/commission-records', methods=['GET'])
@admin_required
def get_commission_records():
    """获取佣金记录列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 筛选条件
        filters = []
        if request.args.get('recipient_address'):
            filters.append(CommissionRecord.recipient_address == request.args.get('recipient_address'))
        if request.args.get('status'):
            filters.append(CommissionRecord.status == request.args.get('status'))
        if request.args.get('commission_type'):
            filters.append(CommissionRecord.commission_type == request.args.get('commission_type'))
        
        # 查询记录
        query = CommissionRecord.query.filter(*filters).order_by(CommissionRecord.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page)
        records = pagination.items
        
        # 生成统计数据
        stats = {
            'total_amount': db.session.query(func.sum(CommissionRecord.amount)).scalar() or 0,
            'pending_amount': db.session.query(func.sum(CommissionRecord.amount)).filter(CommissionRecord.status == 'pending').scalar() or 0,
            'paid_amount': db.session.query(func.sum(CommissionRecord.amount)).filter(CommissionRecord.status == 'paid').scalar() or 0,
            'total_count': CommissionRecord.query.count(),
            'pending_count': CommissionRecord.query.filter_by(status='pending').count(),
            'paid_count': CommissionRecord.query.filter_by(status='paid').count()
        }
        
        return jsonify({
            'success': True,
            'data': [record.to_dict() for record in records],
            'stats': stats,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取佣金记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取佣金记录失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/commission-records/<int:record_id>', methods=['PUT'])
@admin_required
@permission_required('管理佣金')
@log_admin_operation('更新佣金记录')
def update_commission_record(record_id):
    """更新佣金记录状态"""
    try:
        record = CommissionRecord.query.get(record_id)
        if not record:
            return jsonify({
                'success': False,
                'error': f'未找到ID为{record_id}的佣金记录'
            }), 404
        
        data = request.json
        
        # 更新状态字段
        if 'status' in data:
            record.status = data['status']
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '佣金记录更新成功',
            'data': record.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新佣金记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"更新佣金记录失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/commission-records/stats', methods=['GET'])
@admin_required
def get_commission_stats():
    """获取佣金统计数据"""
    try:
        # 统计数据
        stats = {
            # 总体统计
            'total': {
                'amount': db.session.query(func.sum(CommissionRecord.amount)).scalar() or 0,
                'count': CommissionRecord.query.count()
            },
            # 按状态统计
            'by_status': {
                'pending': {
                    'amount': db.session.query(func.sum(CommissionRecord.amount))
                        .filter(CommissionRecord.status == 'pending').scalar() or 0,
                    'count': CommissionRecord.query.filter_by(status='pending').count()
                },
                'paid': {
                    'amount': db.session.query(func.sum(CommissionRecord.amount))
                        .filter(CommissionRecord.status == 'paid').scalar() or 0,
                    'count': CommissionRecord.query.filter_by(status='paid').count()
                },
                'failed': {
                    'amount': db.session.query(func.sum(CommissionRecord.amount))
                        .filter(CommissionRecord.status == 'failed').scalar() or 0,
                    'count': CommissionRecord.query.filter_by(status='failed').count()
                }
            },
            # 按佣金类型统计
            'by_type': {
                'direct': {
                    'amount': db.session.query(func.sum(CommissionRecord.amount))
                        .filter(CommissionRecord.commission_type == 'direct').scalar() or 0,
                    'count': CommissionRecord.query.filter_by(commission_type='direct').count()
                },
                'referral': {
                    'amount': db.session.query(func.sum(CommissionRecord.amount))
                        .filter(CommissionRecord.commission_type == 'referral').scalar() or 0,
                    'count': CommissionRecord.query.filter_by(commission_type='referral').count()
                }
            }
        }
        
        # 最近7天的佣金趋势
        today = datetime.now().date()
        week_ago = today - timedelta(days=6)
        
        # 为每一天创建日期
        date_range = []
        for i in range(7):
            date_range.append((week_ago + timedelta(days=i)).strftime('%Y-%m-%d'))
        
        # 查询每日数据
        daily_stats = []
        for date_str in date_range:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            next_date = date + timedelta(days=1)
            
            daily_amount = db.session.query(func.sum(CommissionRecord.amount)) \
                .filter(CommissionRecord.created_at >= date) \
                .filter(CommissionRecord.created_at < next_date) \
                .scalar() or 0
                
            daily_count = CommissionRecord.query \
                .filter(CommissionRecord.created_at >= date) \
                .filter(CommissionRecord.created_at < next_date) \
                .count()
                
            daily_stats.append({
                'date': date_str,
                'amount': daily_amount,
                'count': daily_count
            })
        
        stats['trend'] = daily_stats
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        current_app.logger.error(f"获取佣金统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取佣金统计失败: {str(e)}"
        }), 500

# 操作日志相关API
@admin_v2_bp.route('/operation-logs', methods=['GET'])
@admin_required
@permission_required('查看日志')
def get_operation_logs():
    """获取管理员操作日志"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 筛选条件
        filters = []
        if request.args.get('admin_address'):
            filters.append(AdminOperationLog.admin_address == request.args.get('admin_address'))
        if request.args.get('operation_type'):
            filters.append(AdminOperationLog.operation_type == request.args.get('operation_type'))
        if request.args.get('target_table'):
            filters.append(AdminOperationLog.target_table == request.args.get('target_table'))
        
        # 日期范围
        if request.args.get('date_from'):
            date_from = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
            filters.append(AdminOperationLog.created_at >= date_from)
        if request.args.get('date_to'):
            date_to = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
            date_to = date_to + timedelta(days=1)  # 包含结束日期整天
            filters.append(AdminOperationLog.created_at <= date_to)
        
        # 查询日志
        query = AdminOperationLog.query.filter(*filters).order_by(AdminOperationLog.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page)
        logs = pagination.items
        
        return jsonify({
            'success': True,
            'data': [log.to_dict() for log in logs],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取操作日志失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取操作日志失败: {str(e)}"
        }), 500

@admin_v2_bp.route('/operation-logs/types', methods=['GET'])
@admin_required
@permission_required('查看日志')
def get_operation_log_types():
    """获取操作日志类型和表名选项"""
    try:
        # 获取所有不同的操作类型
        operation_types = db.session.query(AdminOperationLog.operation_type).distinct().all()
        operation_types = [t[0] for t in operation_types]
        
        # 获取所有不同的表名
        target_tables = db.session.query(AdminOperationLog.target_table).distinct().all()
        target_tables = [t[0] for t in target_tables if t[0] is not None]
        
        return jsonify({
            'success': True,
            'data': {
                'operation_types': operation_types,
                'target_tables': target_tables
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取操作日志类型失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取操作日志类型失败: {str(e)}"
        }), 500 

@admin_v2_bp.route('/asset-types')
@admin_required
def get_asset_types():
    """获取所有资产类型"""
    try:
        # 资产类型数据
        asset_types = [
            {'id': 10, 'name': '不动产', 'code': 'real_estate'},
            {'id': 20, 'name': '商业地产', 'code': 'commercial'},
            {'id': 30, 'name': '工业地产', 'code': 'industrial'},
            {'id': 40, 'name': '土地资产', 'code': 'land'},
            {'id': 50, 'name': '证券资产', 'code': 'securities'},
            {'id': 60, 'name': '艺术品', 'code': 'art'},
            {'id': 70, 'name': '收藏品', 'code': 'collectibles'},
            {'id': 99, 'name': '其他', 'code': 'other'}
        ]
        
        return jsonify({
            'success': True,
            'data': asset_types
        })
        
    except Exception as e:
        current_app.logger.error(f"获取资产类型失败: {str(e)}")
        return jsonify({'success': False, 'error': '获取资产类型失败', 'message': str(e)}), 500