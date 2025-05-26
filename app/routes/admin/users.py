"""
用户管理模块
"""

from flask import render_template, jsonify, request, current_app, g
from sqlalchemy import func, or_, desc
from datetime import datetime, timedelta
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required
from app.extensions import db
from app.models.user import User
from app.models.trade import Trade
from app.models.asset import Asset


@admin_bp.route('/users')
@admin_page_required
def users_page():
    """用户管理页面"""
    return render_template('admin_v2/users.html')

@admin_bp.route('/v2/api/users', methods=['GET'])
@api_admin_required
def users_list_v2():
    """获取用户列表 - V2兼容版本"""
    return get_users_list()

@admin_bp.route('/v2/api/user-stats', methods=['GET'])
@api_admin_required
def user_stats_v2():
    """获取用户统计 - V2兼容版本"""
    return get_user_stats()

@admin_bp.route('/v2/api/users/<address>/set-distributor', methods=['POST'])
@api_admin_required
def set_distributor_v2(address):
    """设置分销商 - V2兼容版本"""
    return set_distributor(address)

@admin_bp.route('/v2/api/users/<address>/block', methods=['POST'])
@api_admin_required
def block_user_v2(address):
    """冻结用户 - V2兼容版本"""
    return block_user(address)

@admin_bp.route('/v2/api/users/<address>/unblock', methods=['POST'])
@api_admin_required
def unblock_user_v2(address):
    """解冻用户 - V2兼容版本"""
    return unblock_user(address)

@admin_bp.route('/v2/api/users/export', methods=['GET'])
@api_admin_required
def export_users_v2():
    """导出用户数据 - V2兼容版本"""
    return export_users()

@admin_bp.route('/api/users', methods=['GET'])
@api_admin_required
def get_users_list():
    """获取用户列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        search = request.args.get('search', '')
        user_type = request.args.get('user_type', '')
        registration_time = request.args.get('registration_time', '')
        
        # 构建查询
        query = User.query
        
        # 搜索条件
        if search:
            query = query.filter(or_(
                User.eth_address.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            ))
        
        # 用户类型过滤
        if user_type == 'verified':
            query = query.filter(User.is_verified == True)
        elif user_type == 'distributor':
            query = query.filter(getattr(User, 'is_distributor', False) == True)
        elif user_type == 'normal':
            query = query.filter(User.is_verified == False)
        
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
            # 获取交易次数（使用正确的字段名）
            trade_count = Trade.query.filter(
                Trade.trader_address == user.eth_address
            ).count()
            
            # 获取持有资产数
            assets_count = Asset.query.filter_by(creator_address=user.eth_address).count()
            
            user_list.append({
                'wallet_address': user.eth_address,
                'username': user.username,
                'email': user.email,
                'role': user.role,  # 添加角色信息
                'status': user.status,  # 添加状态信息
                'is_admin': user.role in ['admin', 'super_admin'],  # 是否为管理员
                'is_verified': bool(user.is_verified),
                'is_distributor': bool(user.is_distributor),
                'is_blocked': bool(user.is_blocked),
                'created_at': user.created_at.isoformat(),
                'trade_count': trade_count,
                'assets_count': assets_count,
                'referrer': user.referrer_address
            })
        
        return jsonify({
            'items': user_list,
            'total': total,
            'pages': total_pages,
            'page': page,
            'page_size': page_size
        })
    
    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def get_user_stats():
    """获取用户统计数据"""
    try:
        # 总用户数
        total_users = User.query.count()
        
        # 已认证用户数
        verified_users = User.query.filter(User.is_verified == True).count()
        
        # 分销商数量
        distributors = User.query.filter(User.is_distributor == True).count()
        
        # 今日新增用户
        today = datetime.utcnow().date()
        new_today = User.query.filter(func.date(User.created_at) == today).count()
        
        return jsonify({
            'totalUsers': total_users,
            'verifiedUsers': verified_users,
            'distributors': distributors,
            'newToday': new_today,
            'activeUsers': verified_users  # 简化版，以认证用户作为活跃用户
        })
    
    except Exception as e:
        current_app.logger.error(f"获取用户统计失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def set_distributor(address):
    """设置用户为分销商"""
    try:
        user = User.query.filter_by(eth_address=address).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        user.is_distributor = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': '用户已设置为分销商'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"设置分销商失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def block_user(address):
    """冻结用户"""
    try:
        user = User.query.filter_by(eth_address=address).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        user.is_blocked = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': '用户已冻结'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"冻结用户失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def unblock_user(address):
    """解冻用户"""
    try:
        user = User.query.filter_by(eth_address=address).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        user.is_blocked = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': '用户已解冻'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"解冻用户失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def export_users():
    """导出用户数据"""
    try:
        import csv
        import io
        
        # 解析查询参数
        search = request.args.get('search', '')
        user_type = request.args.get('user_type', '')
        registration_time = request.args.get('registration_time', '')
        
        # 构建查询
        query = User.query
        
        # 应用筛选条件
        if search:
            query = query.filter(or_(
                User.eth_address.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            ))
        
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
                user.eth_address,
                user.username or '',
                user.email or '',
                user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '是' if user.is_verified else '否',
                '是' if user.is_distributor else '否',
                '是' if user.is_blocked else '否'
            ])
        
        # 设置响应头
        output.seek(0)
        from flask import current_app
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