from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, jsonify, current_app, g, after_this_request, make_response, send_file, send_from_directory, abort
)
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade, TradeStatus, TradeType
from app.models.user import User
from app.models.admin import AdminUser
from app.models.dividend import DividendDistribution, DividendRecord
from sqlalchemy import func, desc, or_, and_
from app.extensions import db
from app.utils.decorators import eth_address_required, admin_required, permission_required, api_admin_required
from app.utils.admin import get_admin_permissions
from app.models.income import PlatformIncome as DBPlatformIncome, IncomeType
from app.models.commission import Commission
from app.models.admin import DashboardStats
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, time, date, timezone
from functools import wraps
import json
import os
from app.utils.storage import storage
import re
import logging
from urllib.parse import urlparse, parse_qs
import random
from app.models.platform_income import PlatformIncome
from app.models.dividend import Dividend
from app.models.admin import AdminUser
from app.models.commission import Commission
from app.models.admin import DashboardStats
from .common import get_pagination_info
import datetime
import calendar
import io
import csv
from app.utils.datetime_compat import get_utc_now, get_utc_today  # 导入兼容函数

# 从routes/__init__.py中获取蓝图
from . import admin_bp, admin_api_bp

def get_admin_info(eth_address):
    """获取管理员权限"""
    if not eth_address:
        return None
        
    # 区分ETH和SOL地址处理
    # ETH地址以0x开头，需要转换为小写
    # SOL地址不以0x开头，保持原样（大小写敏感）
    if eth_address.startswith('0x'):
        normalized_address = eth_address.lower()
    else:
        normalized_address = eth_address
    
    admin_config = current_app.config['ADMIN_CONFIG']
    admin_info = None
    
    # 检查地址是否在管理员配置中
    for admin_address, info in admin_config.items():
        # 同样区分ETH和SOL地址处理
        if admin_address.startswith('0x'):
            config_address = admin_address.lower()
        else:
            config_address = admin_address
            
        if normalized_address == config_address:
            admin_info = info
            break
    
    if admin_info:
        return {
            'is_admin': True,
            'role': admin_info['role'],
            'name': admin_info['name'],
            'level': admin_info['level'],
            'permissions': admin_info['permissions']
        }
    
    return None

def is_admin(eth_address=None):
    """检查指定地址或当前用户是否是管理员"""
    target_address = eth_address if eth_address else g.eth_address if hasattr(g, 'eth_address') else None
    
    if not target_address:
        return False
        
    # 检查是否已经在会话或cookie中有管理员状态
    if session.get('is_admin') and session.get('eth_address') == target_address:
        return True
        
    # 检查cookie
    cookie_address = request.cookies.get('eth_address')
    if request.cookies.get('is_admin') == 'true' and cookie_address == target_address:
        # 更新会话状态
        session['eth_address'] = target_address
        session['is_admin'] = True
        return True
    
    # 从配置中检查管理员
    admin_info = get_admin_info(target_address)
    
    # 使用兼容的旧方法检查
    if not admin_info:
        if hasattr(current_app.config, 'ADMIN_ADDRESSES') and target_address in current_app.config.get('ADMIN_ADDRESSES', []):
            current_app.logger.info(f'使用ADMIN_ADDRESSES检查成功: {target_address}')
            return True
            
    return admin_info is not None

def has_permission(permission, eth_address=None):
    """检查管理员是否有特定权限"""
    target_address = eth_address if eth_address else g.eth_address if hasattr(g, 'eth_address') else None
    admin_info = get_admin_info(target_address)
    
    if not admin_info:
        return False
        
    # 检查权限等级
    required_level = current_app.config['PERMISSION_LEVELS'].get(permission, 1)  # 默认需要最高权限
    if admin_info['level'] <= required_level:  # 级别数字越小，权限越大
        return True
        
    # 如果没有通过等级检查，则检查具体权限列表
    return permission in admin_info['permissions']

def get_admin_role(eth_address=None):
    """获取管理员角色信息"""
    target_address = eth_address if eth_address else g.eth_address if hasattr(g, 'eth_address') else None
    admin_info = get_admin_info(target_address)
    if admin_info:
        return {
            'role': admin_info['role'],
            'name': admin_info['name'],
            'level': admin_info['level'],
            'permissions': admin_info['permissions']
        }
    return None

def admin_required(f):
    """管理员权限装饰器"""
    @eth_address_required
    def admin_check(*args, **kwargs):
        # 检查是否为管理员
        admin = AdminUser.query.filter_by(wallet_address=g.eth_address).first()
        if not admin:
            flash('需要管理员权限')
            return redirect(url_for('main.index'))
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
                flash(f'需要{permission}权限')
                return redirect(url_for('admin.dashboard'))
            return f(*args, **kwargs)
        permission_check.__name__ = f.__name__
        return permission_check
    return decorator

def admin_page_required(f):
    """管理页面权限装饰器，用于网页访问"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 记录详细的请求信息，帮助排查问题
        current_app.logger.info(f"访问管理页面: {request.path}")
        current_app.logger.info(f"请求头: {dict(request.headers)}")
        current_app.logger.info(f"Cookies: {request.cookies}")
        current_app.logger.info(f"Session: {session}")
        
        # 尝试从各种来源获取钱包地址
        eth_address = None
        
        # 检查请求头
        if 'X-Eth-Address' in request.headers:
            eth_address = request.headers.get('X-Eth-Address')
            current_app.logger.info(f"从请求头获取钱包地址: {eth_address}")
        
        # 检查Cookie
        if not eth_address and 'eth_address' in request.cookies:
            eth_address = request.cookies.get('eth_address')
            current_app.logger.info(f"从Cookie获取钱包地址: {eth_address}")
        
        # 检查会话
        if not eth_address and 'eth_address' in session:
            eth_address = session.get('eth_address')
            current_app.logger.info(f"从Session获取钱包地址: {eth_address}")
        
        if not eth_address and 'admin_eth_address' in session:
            eth_address = session.get('admin_eth_address')
            current_app.logger.info(f"从Session获取管理员钱包地址: {eth_address}")
        
        # 尝试从URL参数获取
        if not eth_address and 'eth_address' in request.args:
            eth_address = request.args.get('eth_address')
            current_app.logger.info(f"从URL参数获取钱包地址: {eth_address}")
        
        current_app.logger.info(f"最终使用的钱包地址: {eth_address}")
        
        # 验证是否为管理员，如果不是管理员，但路径中有v2，返回当前V2管理页面
        if not eth_address or not is_admin(eth_address):
            if '/v2/' in request.path or request.path.endswith('/v2'):
                # 如果请求是V2路径，返回登录页面
                current_app.logger.info("重定向到管理员登录页面(V2)")
                return redirect(url_for('admin.login_v2'))
            else:
                # 添加简单的调试日志
                current_app.logger.info("非V2路径，普通重定向")
                flash('请先连接钱包并验证管理员身份', 'warning')
                return redirect(url_for('main.index'))
        
        # 如果是管理员，设置当前会话和临时变量
        g.eth_address = eth_address
        g.admin_info = get_admin_info(eth_address)
        
        # 更新session，确保后续请求正常
        session['eth_address'] = eth_address
        session['admin_eth_address'] = eth_address
        
        @after_this_request
        def set_cookie(response):
            response.set_cookie('eth_address', eth_address, max_age=3600*24*30)
            return response
        
        current_app.logger.info(f"通过管理员验证，用户: {eth_address}")
        return f(*args, **kwargs)
    return decorated_function

# 页面路由
@admin_bp.route('/')
@admin_page_required
def index():
    """后台管理首页"""
    try:
        # 直接使用g对象中的管理员信息
        admin_info = g.admin_info
        eth_address = g.eth_address
        
        current_app.logger.info(f'管理员访问后台首页: {eth_address}')
        
        return render_template('admin/dashboard.html', admin_info=admin_info)
    except Exception as e:
        current_app.logger.warning(f'访问后台管理页面失败：{str(e)}')
        return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
@admin_page_required
def dashboard():
    """后台管理仪表板"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/distribution')
@admin_page_required
def distribution():
    """分销管理页面"""
    return render_template('admin/distribution.html')

@admin_bp.route('/commission_settings')
@admin_page_required
def commission_settings():
    """佣金设置页面"""
    return render_template('admin/commission_settings.html')

@admin_bp.route('/commission_records')
@admin_page_required
def commission_records():
    """佣金记录页面"""
    return render_template('admin/commission_records.html')

@admin_bp.route('/operation_logs')
@admin_page_required
def operation_logs():
    """操作日志页面"""
    return render_template('admin/operation_logs.html')

@admin_bp.route('/assets/<int:asset_id>/edit')
@admin_page_required
def edit_asset(asset_id):
    """编辑资产页面"""
    try:
        # 获取资产信息
        asset = Asset.query.get_or_404(asset_id)
        return render_template('admin/edit_asset.html', asset_id=asset_id)
    except Exception as e:
        current_app.logger.error(f'加载编辑资产页面失败: {str(e)}')
        return redirect(url_for('admin.dashboard', eth_address=g.eth_address))

@admin_bp.route('/assets')
@admin_page_required
def assets():
    """资产管理页面"""
    try:
        # 获取所有资产
        assets = Asset.query.all()
        return render_template('admin/assets.html', assets=assets)
    except Exception as e:
        current_app.logger.warning(f'资产管理页面加载失败: {str(e)}')
        flash('资产数据加载失败', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/users')
@admin_page_required
def users():
    """用户管理页面"""
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        current_app.logger.warning(f'用户管理页面加载失败: {str(e)}')
        flash('用户数据加载失败', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/trades')
@admin_page_required
def trades():
    """交易管理页面"""
    try:
        trades = Trade.query.order_by(Trade.created_at.desc()).all()
        return render_template('admin/trades.html', trades=trades)
    except Exception as e:
        current_app.logger.warning(f'交易管理页面加载失败: {str(e)}')
        flash('交易数据加载失败', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/export/assets')
@admin_page_required
def export_assets():
    """导出资产数据"""
    try:
        # 获取所有资产
        assets = Asset.query.all()
        
        # 创建CSV文件
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['ID', '名称', '代币符号', '发行方', '状态', '总供应量', '价格'])
        
        # 写入数据
        for asset in assets:
            writer.writerow([
                asset.id,
                asset.name,
                asset.token_symbol,
                asset.issuer,
                asset.status,
                asset.total_supply,
                asset.price
            ])
        
        # 返回CSV文件
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'assets_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
        )
    except Exception as e:
        current_app.logger.warning(f'导出资产数据失败: {str(e)}')
        flash('导出资产数据失败', 'danger')
        return redirect(url_for('admin.assets'))

@admin_bp.route('/export/users')
@admin_page_required
def export_users():
    """导出用户数据"""
    try:
        # 获取所有用户
        users = User.query.all()
        
        # 创建CSV文件
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['ID', '用户名', '邮箱', '钱包地址', '注册时间'])
        
        # 写入数据
        for user in users:
            writer.writerow([
                user.id,
                user.username,
                user.email,
                user.wallet_address,
                user.created_at
            ])
        
        # 返回CSV文件
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'users_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
        )
    except Exception as e:
        current_app.logger.warning(f'导出用户数据失败: {str(e)}')
        flash('导出用户数据失败', 'danger')
        return redirect(url_for('admin.users'))

@admin_bp.route('/export/trades')
@admin_page_required
def export_trades():
    """导出交易数据"""
    try:
        # 获取所有交易
        trades = Trade.query.all()
        
        # 创建CSV文件
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['ID', '资产ID', '用户ID', '数量', '金额', '状态', '创建时间'])
        
        # 写入数据
        for trade in trades:
            writer.writerow([
                trade.id,
                trade.asset_id,
                trade.user_id,
                trade.quantity,
                trade.amount,
                trade.status,
                trade.created_at
            ])
        
        # 返回CSV文件
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'trades_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
        )
    except Exception as e:
        current_app.logger.warning(f'导出交易数据失败: {str(e)}')
        flash('导出交易数据失败', 'danger')
        return redirect(url_for('admin.trades'))

@admin_bp.route('/logout')
def logout():
    """退出登录，重定向到首页"""
    try:
        return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f'退出登录失败: {str(e)}')
        return redirect('/')

# API路由
@admin_api_bp.route('/stats')
def get_admin_stats():
    """获取管理仪表盘统计数据"""
    try:
        # 检查是否提供了钱包地址
        eth_address = None
        if 'X-Eth-Address' in request.headers:
            eth_address = request.headers.get('X-Eth-Address')
        if not eth_address and 'eth_address' in request.cookies:
            eth_address = request.cookies.get('eth_address')
        if not eth_address and 'eth_address' in session:
            eth_address = session.get('eth_address')
        if not eth_address and 'admin_eth_address' in session:
            eth_address = session.get('admin_eth_address')
        
        # 记录请求
        current_app.logger.info(f"访问统计API，地址: {eth_address}")
        
        # 当前日期
        today = datetime.now(timezone.utc).replace(tzinfo=None).date()
        
        # 查询DashboardStats表中的统计数据
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
        
        # 如果统计数据不完整，则更新统计数据
        if len(stats) < 6:  # 至少应有6种统计数据
            if not DashboardStats.update_stats_from_db():
                DashboardStats.update_daily_stats()
            
            # 再次查询更新后的统计数据
            stats = {}
            all_stats = DashboardStats.query.filter(
                DashboardStats.stat_date == today,
                DashboardStats.stat_period == 'daily'
            ).all()
            
            for stat in all_stats:
                stats[stat.stat_type] = stat.stat_value
        
        # 返回格式化的数据
        return jsonify({
            'total_users': stats.get('user_count', 0),
            'new_users_today': stats.get('new_users', 0),
            'new_users_week': stats.get('new_users_week', 0),
            'total_assets': stats.get('asset_count', 0),
            'total_asset_value': stats.get('asset_value', 0),
            'total_trades': stats.get('trade_count', 0),
            'total_trade_volume': stats.get('trade_volume', 0)
        })
    except Exception as e:
        current_app.logger.error(f"获取管理仪表盘统计数据失败: {str(e)}", exc_info=True)
        return jsonify({
            'total_users': 0,
            'new_users_today': 0,
            'new_users_week': 0,
            'total_assets': 0,
            'total_asset_value': 0,
            'total_trades': 0,
            'total_trade_volume': 0
        })

@admin_api_bp.route('/pending-assets')
@admin_required
def list_pending_assets():
    """获取待审核资产列表"""
    try:
        print('开始查询待审核资产...')
        assets = Asset.query.filter_by(status=AssetStatus.PENDING)\
                          .order_by(Asset.created_at.desc())\
                          .all()
        print(f'找到 {len(assets)} 个待审核资产')
        
        # 转换资产数据为字典格式
        asset_list = []
        for asset in assets:
            try:
                print(f'处理资产 ID: {asset.id}')
                asset_dict = asset.to_dict()
                print(f'资产数据: {asset_dict}')
                asset_list.append(asset_dict)
            except Exception as e:
                print(f'转换资产 {asset.id} 数据失败: {str(e)}')
                continue
        
        response_data = {
            'assets': asset_list,
            'total': len(asset_list)
        }
        print(f'返回数据: {response_data}')
        return jsonify(response_data)
        
    except Exception as e:
        print(f'获取待审核资产列表失败: {str(e)}')
        return jsonify({
            'error': '获取待审核资产列表失败',
            'message': str(e)
        }), 500

@admin_api_bp.route('/assets/<int:asset_id>/approve', methods=['POST'])
@admin_required
def approve_admin_asset(asset_id):
    """审核通过资产"""
    if not has_permission('审核'):
        return jsonify({'error': '没有审核权限'}), 403
        
    asset = Asset.query.get_or_404(asset_id)
    current_app.logger.info(f'审核资产 {asset_id}:')
    current_app.logger.info(f'当前状态: {asset.status}')
    current_app.logger.info(f'待审核状态值: {AssetStatus.PENDING.value}')
    current_app.logger.info(f'状态比较结果: {asset.status != AssetStatus.PENDING.value}')
    
    if asset.status != AssetStatus.PENDING.value:  # 使用 .value 确保比较数值
        current_app.logger.warning(f'资产状态不匹配: 当前={asset.status}, 需要={AssetStatus.PENDING.value}')
        return jsonify({'error': '该资产不在待审核状态'}), 400
        
    try:
        asset.status = AssetStatus.APPROVED.value  # 使用 .value 确保设置数值
        asset.approved_at = get_utc_now()
        db.session.commit()
        current_app.logger.info(f'资产 {asset_id} 审核通过')
        return jsonify({'message': '审核通过成功'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'审核失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/assets/<int:asset_id>/reject', methods=['POST'])
@admin_required
def reject_admin_asset(asset_id):
    """拒绝资产"""
    if not has_permission('审核'):
        return jsonify({'error': '没有审核权限'}), 403
        
    data = request.get_json()
    if not data or not data.get('reason'):
        return jsonify({'error': '请提供拒绝原因'}), 400
        
    asset = Asset.query.get_or_404(asset_id)
    if asset.status != AssetStatus.PENDING:
        return jsonify({'error': '该资产不在待审核状态'}), 400
        
    try:
        asset.status = AssetStatus.REJECTED.value
        asset.reject_reason = data['reason']
        db.session.commit()
        return jsonify({'message': '已拒绝该资产'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/assets', methods=['GET'])
@admin_required
def list_all_assets():
    """列出所有资产"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '')
        
        # 查询资产
        query = Asset.query
        
        # 过滤掉已删除的资产
        query = query.filter(
            Asset.status.in_([
                AssetStatus.PENDING.value,
                AssetStatus.APPROVED.value,
                AssetStatus.REJECTED.value
            ])
        )
        
        # 搜索条件
        if search:
            query = query.filter(
                db.or_(
                    Asset.name.like(f'%{search}%'),
                    Asset.description.like(f'%{search}%'),
                    Asset.token_symbol.like(f'%{search}%')
                )
            )
        
        # 获取分页数据
        paginated_assets = query.order_by(Asset.id.desc()).paginate(page=page, per_page=limit, error_out=False)
        
        # 转换为JSON格式
        assets_list = []
        for asset in paginated_assets.items:
            try:
                asset_dict = asset.to_dict()
                # 添加销售额字段
                sold_tokens = (asset.token_supply or 0) - (asset.remaining_supply or 0)
                asset_dict['sales_volume'] = float(sold_tokens * (asset.token_price or 0))
                assets_list.append(asset_dict)
            except Exception as e:
                current_app.logger.error(f'转换资产数据失败 (ID: {asset.id}): {str(e)}')
                continue
        
        return jsonify({
            'page': page,
            'limit': limit,
            'total': paginated_assets.total,
            'assets': assets_list
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取资产列表失败',
            'message': str(e)
        }), 500

@admin_api_bp.route('/assets/<int:asset_id>', methods=['DELETE'])
@admin_required
def delete_asset(asset_id):
    """删除资产"""
    try:
        current_app.logger.info(f'删除资产请求: asset_id={asset_id}')
        
        # 查找资产
        asset = Asset.query.get_or_404(asset_id)
        
        # 如果资产已上链，不允许删除
        if asset.token_address:
            return jsonify({'error': '已上链资产不可删除'}), 400
            
        try:
            # 删除关联的分红记录
            DividendRecord.query.filter_by(asset_id=asset_id).delete()
            
            # 删除关联的交易记录
            Trade.query.filter_by(asset_id=asset_id).delete()
            
            # 删除资产记录
            db.session.delete(asset)
            db.session.commit()
            
            current_app.logger.info(f'资产已删除: {asset_id}')
            return jsonify({'message': '资产已删除'})
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'删除资产失败: {str(e)}')
            return jsonify({'error': f'删除资产失败: {str(e)}'}), 500
            
    except Exception as e:
        current_app.logger.error(f'删除资产失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/assets/batch-delete', methods=['POST'])
@admin_required
def batch_delete_assets():
    """批量删除资产"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'success': False, 'error': '请提供要删除的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        current_app.logger.info(f'批量删除资产请求: asset_ids={asset_ids}')
        
        # 确保ID是整数
        for i, asset_id in enumerate(asset_ids):
            if isinstance(asset_id, str):
                try:
                    asset_ids[i] = int(asset_id)
                except ValueError:
                    pass  # 如果无法转换，保持原样
        
        success_count = 0
        failed_ids = []
        
        for asset_id in asset_ids:
            try:
                asset = Asset.query.get(asset_id)
                
                if not asset:
                    failed_ids.append({"id": asset_id, "reason": "资产不存在"})
                    continue
                
                # 删除关联记录
                DividendRecord.query.filter_by(asset_id=asset_id).delete()
                Trade.query.filter_by(asset_id=asset_id).delete()
                
                # 删除资产
                db.session.delete(asset)
                success_count += 1
                
            except Exception as e:
                current_app.logger.error(f'删除资产 {asset_id} 失败: {str(e)}')
                failed_ids.append({"id": asset_id, "reason": str(e)})
                continue
                
        db.session.commit()
        
        message = f'成功删除 {success_count} 个资产'
        if failed_ids:
            message += f'，{len(failed_ids)} 个资产删除失败'
            
        return jsonify({
            'success': True,
            'message': message,
            'success_count': success_count,
            'failed_count': len(failed_ids),
            'failed_ids': failed_ids
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量删除资产失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_api_bp.route('/check_asset/<int:asset_id>', methods=['GET', 'OPTIONS'])
def check_asset_owner(asset_id):
    """检查资产所有者和管理权限"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'})
        
    try:
        asset = Asset.query.get_or_404(asset_id)
        eth_address = request.headers.get('X-Eth-Address', '').lower()
        
        # 检查是否是资产所有者
        is_owner = eth_address and eth_address == asset.owner_address.lower()
        
        # 检查是否是管理员
        admin_info = None
        if eth_address:
            admin_config = current_app.config['ADMIN_CONFIG']
            admin_config = {k.lower(): v for k, v in admin_config.items()}
            admin_info = admin_config.get(eth_address)
        
        # 检查分红管理权限
        can_manage_dividend = False
        if is_owner:
            can_manage_dividend = True
        elif admin_info:
            # 主管理员或有审核权限的管理员可以管理分红
            can_manage_dividend = admin_info.get('level', 999) == 1 or '审核' in admin_info.get('permissions', [])
        
        return jsonify({
            'is_owner': is_owner,
            'owner_address': asset.owner_address,
            'is_admin': admin_info is not None,
            'admin_info': {
                'role': admin_info['role'] if admin_info else None,
                'permissions': admin_info['permissions'] if admin_info else []
            } if admin_info else None,
            'can_manage_dividend': can_manage_dividend
        })
    except Exception as e:
        current_app.logger.error(f'检查资产权限失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '检查资产权限失败',
            'message': str(e)
        }), 500

# 优化现有的 check_admin 端点
@admin_api_bp.route('/check', methods=['POST', 'GET'])
def check_admin():
    """检查管理员权限"""
    try:
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     session.get('admin_eth_address')
                     
        current_app.logger.info(f'检查管理员权限 - 原始地址: {eth_address}')
        
        if not eth_address:
            current_app.logger.warning('未提供钱包地址')
            return jsonify({'is_admin': False}), 200
            
        # 区分ETH和SOL地址处理，ETH地址转小写，SOL地址保持原样
        if eth_address.startswith('0x'):
            normalized_address = eth_address.lower()
            current_app.logger.info(f'检查管理员权限 - ETH地址(小写): {normalized_address}')
        else:
            normalized_address = eth_address
            current_app.logger.info(f'检查管理员权限 - 非ETH地址(原样): {normalized_address}')
        
        admin_data = get_admin_info(normalized_address)
        is_admin = bool(admin_data)
        
        if not is_admin:
            current_app.logger.warning('未找到管理员权限')
            session.pop('admin_eth_address', None)
            session.pop('admin_info', None)
        else:
            session['admin_eth_address'] = normalized_address
            session['admin_info'] = admin_data
        
        current_app.logger.info(f'检查管理员权限 - 结果: {is_admin}')
        return jsonify({'is_admin': is_admin, **(admin_data or {})}), 200
    except Exception as e:
        current_app.logger.error(f'检查管理员权限失败: {str(e)}')
        return jsonify({'is_admin': False, 'error': str(e)}), 500

@admin_api_bp.route('/admins')
@admin_required
def get_admin_list():
    """获取管理员列表"""
    admin_list = []
    admin_config = current_app.config['ADMIN_CONFIG']
    
    for address, info in admin_config.items():
        admin_list.append({
            'address': address,
            'role': info['role'],
            'name': info.get('name', ''),  # 添加名字字段
            'level': info.get('level', 1),  # 添加级别字段
            'permissions': info['permissions']
        })
    return jsonify({'admins': admin_list}) 

@admin_api_bp.route('/assets/<int:asset_id>/dividend_stats', methods=['GET'])
def get_dividend_stats(asset_id):
    """获取资产分红统计信息"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 获取分红统计信息
        total_amount = db.session.query(db.func.sum(DividendRecord.amount))\
            .filter(DividendRecord.asset_id == asset_id)\
            .scalar() or 0
            
        count = DividendRecord.query.filter_by(asset_id=asset_id).count()
        
        stats = {
            'count': count,  # 分红次数
            'total_amount': float(total_amount),  # 总分红金额
        }
        
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f'获取分红统计失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取分红统计失败',
            'message': str(e)
        }), 500

@admin_api_bp.route('/assets/<int:asset_id>/dividend_history', methods=['GET'])
def get_dividend_history(asset_id):
    """获取资产分红历史"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 获取分红历史记录
        records = DividendRecord.query\
            .filter_by(asset_id=asset_id)\
            .order_by(DividendRecord.created_at.desc())\
            .all()
            
        total_amount = sum(record.amount for record in records)
        
        history = {
            'total_amount': float(total_amount),  # 累计分红金额
            'records': [record.to_dict() for record in records]  # 分红记录列表
        }
        
        return jsonify(history)
    except Exception as e:
        current_app.logger.error(f'获取分红历史失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取分红历史失败',
            'message': str(e)
        }), 500

@admin_api_bp.route('/assets/approve', methods=['POST'])
@admin_required
@permission_required('审核')
def approve_assets():
    """审核资产"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'error': '缺少资产ID'}), 400
            
        asset_ids = data['asset_ids']
        if not isinstance(asset_ids, list):
            asset_ids = [asset_ids]
            
        # 获取要审核的资产
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()
        if not assets:
            return jsonify({'error': '未找到指定的资产'}), 404
            
        # 检查资产状态
        for asset in assets:
            if asset.status != AssetStatus.PENDING:
                return jsonify({'error': f'资产 {asset.id} 状态不正确'}), 400
                
        # 更新资产状态
        for asset in assets:
            asset.status = AssetStatus.APPROVED.value
            asset.approved_at = get_utc_now()
            asset.approved_by = g.eth_address
            
        try:
            db.session.commit()
            return jsonify({
                'message': '审核成功',
                'approved_assets': [asset.id for asset in assets]
            }), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'保存审核状态失败: {str(e)}', exc_info=True)
            return jsonify({'error': '保存审核状态失败'}), 500
            
    except Exception as e:
        current_app.logger.error(f'审核资产失败: {str(e)}', exc_info=True)
        return jsonify({'error': '审核资产失败'}), 500 

@admin_api_bp.route('/assets/batch-approve', methods=['POST'])
@admin_required
def batch_approve_assets():
    """批量审核资产"""
    try:
        # 获取要审核的资产ID列表
        asset_ids = request.json.get('asset_ids', [])
        if not asset_ids:
            return jsonify({'error': '未选择要审核的资产'}), 400
            
        eth_address = g.eth_address
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()
        
        if not assets:
            return jsonify({'error': '未找到要审核的资产'}), 404

        # 批量审核资产
        for asset in assets:
            if asset.status != AssetStatus.PENDING.value:
                continue
                
            # 更新资产状态
            asset.status = AssetStatus.APPROVED.value
            asset.approved_at = get_utc_now()
            asset.approved_by = eth_address
            
            # 不需要移动文件，因为已经存储在七牛云上
            
        db.session.commit()
        return jsonify({'message': f'成功审核 {len(assets)} 个资产'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量审核资产失败: {str(e)}')
        return jsonify({'error': '批量审核资产失败'}), 500

@admin_api_bp.route('/assets/<int:asset_id>', methods=['GET'])
@admin_required
def get_admin_asset(asset_id):
    """获取单个资产信息"""
    try:
        current_app.logger.info(f'获取资产信息 - ID: {asset_id}')
        asset = Asset.query.get_or_404(asset_id)
        
        # 转换资产数据为字典格式
        asset_data = asset.to_dict()
        current_app.logger.info(f'资产数据: {asset_data}')
        
        return jsonify(asset_data), 200
        
    except Exception as e:
        current_app.logger.error(f'获取资产信息失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取资产信息失败',
            'message': str(e)
        }), 500 

@admin_bp.route('/admin_addresses', methods=['GET'])
@admin_required
@permission_required('管理用户')
def admin_addresses_page():
    """管理员地址管理页面"""
    admin_config = current_app.config.get('ADMIN_CONFIG', {})
    return render_template('admin/admin_addresses.html', admin_config=admin_config)

@admin_bp.route('/api/admin_addresses', methods=['GET'])
@admin_required
@permission_required('管理用户')
def get_admin_addresses():
    """获取管理员地址列表"""
    admin_config = current_app.config.get('ADMIN_CONFIG', {})
    admin_list = []
    
    for address, info in admin_config.items():
        admin_list.append({
            'address': address,
            'name': info.get('name', '管理员'),
            'role': info.get('role', 'admin'),
            'level': info.get('level', 1),
            'permissions': info.get('permissions', [])
        })
    
    return jsonify({'admin_addresses': admin_list})

@admin_bp.route('/api/admin_addresses', methods=['POST'])
@admin_required
@permission_required('管理用户')
def add_admin_address():
    """添加管理员地址"""
    data = request.json
    
    if not data or 'address' not in data:
        return jsonify({'error': '请提供管理员地址'}), 400
    
    address = data['address'].lower()
    name = data.get('name', '管理员')
    role = data.get('role', 'admin')
    level = data.get('level', 2)  # 默认为二级管理员
    permissions = data.get('permissions', ['审核', '编辑', '查看统计'])
    
    # 验证地址格式
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({'error': '无效的以太坊地址格式'}), 400
    
    # 检查地址是否已存在
    admin_config = current_app.config.get('ADMIN_CONFIG', {})
    if address in [addr.lower() for addr in admin_config.keys()]:
        return jsonify({'error': '该地址已是管理员'}), 400
    
    # 添加新管理员
    admin_config[address] = {
        'name': name,
        'role': role,
        'level': level,
        'permissions': permissions
    }
    
    # 更新配置
    current_app.config['ADMIN_CONFIG'] = admin_config
    
    # 在实际应用中，这里应该将更新持久化到数据库或配置文件
    # 这里仅为示例，实际实现需要根据应用架构调整
    
    return jsonify({
        'success': True,
        'message': '管理员地址添加成功',
        'admin': {
            'address': address,
            'name': name,
            'role': role,
            'level': level,
            'permissions': permissions
        }
    })

@admin_bp.route('/api/admin_addresses/<address>', methods=['DELETE'])
@admin_required
@permission_required('管理用户')
def remove_admin_address(address):
    """删除管理员地址"""
    address = address.lower()
    
    # 获取当前管理员配置
    admin_config = current_app.config.get('ADMIN_CONFIG', {})
    
    # 检查地址是否存在
    address_found = False
    for admin_address in list(admin_config.keys()):
        if admin_address.lower() == address:
            address_found = True
            # 不允许删除超级管理员
            if admin_config[admin_address].get('level') == 1:
                return jsonify({'error': '不能删除超级管理员'}), 403
            
            # 删除管理员
            del admin_config[admin_address]
            break
    
    if not address_found:
        return jsonify({'error': '管理员地址不存在'}), 404
    
    # 更新配置
    current_app.config['ADMIN_CONFIG'] = admin_config
    
    # 在实际应用中，这里应该将更新持久化到数据库或配置文件
    # 这里仅为示例，实际实现需要根据应用架构调整
    
    return jsonify({
        'success': True,
        'message': '管理员地址删除成功'
    })

@admin_api_bp.route('/visit-stats', methods=['GET'])
@admin_required
def get_visit_stats():
    """获取系统访问量统计数据"""
    try:
        # 获取传入的时间周期参数
        period = request.args.get('period', 'daily')
        
        # 当前日期时间
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today = now.date()
        
        labels = []
        values = []
        
        # 使用Trade或Asset创建记录作为访问量的替代指标
        # 在实际系统中，应该使用专门的访问日志表
        if period == 'daily':
            # 获取最近24小时的数据
            for i in range(24):
                # 计算小时时间段
                # 从当前时间减去i小时
                delta_hours = i
                hour_start = now - timedelta(hours=delta_hours)
                hour_start = hour_start.replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start.replace(minute=59, second=59, microsecond=999999)
                
                # 小时标签
                hour_label = hour_start.strftime('%H:00')
                labels.append(hour_label)
                
                # 统计该小时的交易或资产创建数量作为访问量的替代指标
                count_trades = db.session.query(func.count(Trade.id))\
                    .filter(Trade.created_at.between(hour_start, hour_end))\
                    .scalar() or 0
                    
                count_assets = db.session.query(func.count(Asset.id))\
                    .filter(Asset.created_at.between(hour_start, hour_end))\
                    .scalar() or 0
                
                # 合并作为访问量
                visit_count = count_trades + count_assets
                values.append(visit_count)
                
        elif period == 'weekly':
            # 获取最近7天的数据
            for i in range(6, -1, -1):
                day_date = today - timedelta(days=i)
                day_start = datetime.combine(day_date, datetime.min.time())
                day_end = datetime.combine(day_date, datetime.max.time())
                
                # 日期标签
                day_label = day_date.strftime('%m-%d')
                labels.append(day_label)
                
                # 统计当天的交易或资产创建数量
                count_trades = db.session.query(db.func.count(Trade.id))\
                    .filter(Trade.created_at.between(day_start, day_end))\
                    .scalar() or 0
                    
                count_assets = db.session.query(db.func.count(Asset.id))\
                    .filter(Asset.created_at.between(day_start, day_end))\
                    .scalar() or 0
                
                # 合并并乘以因子作为访问量估计值(访问量通常是交易量的倍数)
                visit_count = (count_trades + count_assets) * 5  # 假设访问量是交易和资产创建总数的5倍
                values.append(visit_count)
                
        elif period == 'monthly':
            # 获取最近30天的数据，按周聚合
            for i in range(3, -1, -1):
                # 计算周的起止时间
                week_start = today - timedelta(days=today.weekday() + i*7)
                week_end = week_start + timedelta(days=6)
                
                week_start_dt = datetime.combine(week_start, datetime.min.time())
                week_end_dt = datetime.combine(week_end, datetime.max.time())
                
                # 避免未来的日期
                if week_end > today:
                    week_end = today
                    week_end_dt = datetime.combine(week_end, datetime.max.time())
                
                # 周标签
                week_label = f"{week_start.strftime('%m-%d')}~{week_end.strftime('%m-%d')}"
                labels.append(week_label)
                
                # 统计该周的交易或资产创建数量
                count_trades = db.session.query(db.func.count(Trade.id))\
                    .filter(Trade.created_at.between(week_start_dt, week_end_dt))\
                    .scalar() or 0
                    
                count_assets = db.session.query(db.func.count(Asset.id))\
                    .filter(Asset.created_at.between(week_start_dt, week_end_dt))\
                    .scalar() or 0
                
                # 合并并乘以因子作为访问量估计值
                visit_count = (count_trades + count_assets) * 10  # 假设访问量是交易和资产创建总数的10倍
                values.append(visit_count)
        
        # 如果没有数据，提供空数据结构
        if not labels or sum(values) == 0:
            if period == 'daily':
                labels = [f"{i:02d}:00" for i in range(24)]
                values = [0] * 24
            elif period == 'weekly':
                labels = [(today - timedelta(days=i)).strftime('%m-%d') for i in range(6, -1, -1)]
                values = [0] * 7
            else:
                labels = ['暂无数据']
                values = [0]
        
        return jsonify({
            'labels': labels,
            'values': values
        })
        
    except Exception as e:
        current_app.logger.error(f'获取访问量统计失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取访问量统计失败',
            'message': str(e)
        }), 500

@admin_api_bp.route('/income-stats')
@admin_required
def get_income_stats():
    """获取平台收入统计数据"""
    try:
        current_app.logger.info("获取平台收入统计数据")
        
        # 获取总交易手续费
        total_trade_fee = db.session.query(func.sum(DBPlatformIncome.amount))\
            .filter(DBPlatformIncome.type == IncomeType.TRANSACTION.value)\
            .scalar() or 0
            
        # 获取总链上服务费
        total_onchain_fee = db.session.query(func.sum(DBPlatformIncome.amount))\
            .filter(DBPlatformIncome.type == IncomeType.ASSET_ONCHAIN.value)\
            .scalar() or 0
            
        # 获取总分红手续费
        total_dividend_fee = db.session.query(func.sum(DBPlatformIncome.amount))\
            .filter(DBPlatformIncome.type == IncomeType.DIVIDEND.value)\
            .scalar() or 0
            
        # 计算总收入
        total_income = total_trade_fee + total_onchain_fee + total_dividend_fee
        
        # 计算各类收入占比
        trade_fee_percent = round((total_trade_fee / total_income * 100) if total_income > 0 else 0, 2)
        onchain_fee_percent = round((total_onchain_fee / total_income * 100) if total_income > 0 else 0, 2)
        dividend_fee_percent = round((total_dividend_fee / total_income * 100) if total_income > 0 else 0, 2)
        
        # 获取今日交易手续费
        today = get_utc_today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_trade_fee = db.session.query(func.sum(DBPlatformIncome.amount))\
            .filter(
                DBPlatformIncome.type == IncomeType.TRANSACTION.value,
                DBPlatformIncome.created_at.between(today_start, today_end)
            )\
            .scalar() or 0
            
        # 获取昨日交易手续费，用于计算环比
        yesterday = today - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())
        
        yesterday_trade_fee = db.session.query(func.sum(DBPlatformIncome.amount))\
            .filter(
                DBPlatformIncome.type == IncomeType.TRANSACTION.value,
                DBPlatformIncome.created_at.between(yesterday_start, yesterday_end)
            )\
            .scalar() or 0
            
        # 计算环比
        day_over_day = 0
        if yesterday_trade_fee > 0:
            day_over_day = round((today_trade_fee - yesterday_trade_fee) / yesterday_trade_fee * 100, 2)
        
        # 获取当前费率设置
        fee_settings = get_current_fee_settings()
        
        # 获取近30天收入趋势
        income_trend = get_income_trend(30)
        
        return jsonify({
            'total_income': round(total_income, 2),
            'total_trade_fee': round(total_trade_fee, 2),
            'total_onchain_fee': round(total_onchain_fee, 2),
            'total_dividend_fee': round(total_dividend_fee, 2),
            'trade_fee_percent': trade_fee_percent,
            'onchain_fee_percent': onchain_fee_percent,
            'dividend_fee_percent': dividend_fee_percent,
            'today_trade_fee': round(today_trade_fee, 2),
            'day_over_day': day_over_day,
            'current_settings': fee_settings,
            'income_trend': income_trend
        })
        
    except Exception as e:
        current_app.logger.error(f'获取平台收入统计失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取平台收入统计失败',
            'message': str(e)
        }), 500
        
def get_income_trend(days=30):
    """获取近期收入趋势
    
    Args:
        days: 天数，默认30天
        
    Returns:
        dict: 包含标签和数值的字典
    """
    labels = []
    values = []
    
    today = datetime.utcnow().date()
    
    # 按天统计收入
    for i in range(days-1, -1, -1):
        day_date = today - timedelta(days=i)
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())
        
        # 日期标签
        day_label = day_date.strftime('%m-%d')
        labels.append(day_label)
        
        # 查询当天总收入
        day_income = db.session.query(func.sum(DBPlatformIncome.amount))\
            .filter(DBPlatformIncome.created_at.between(day_start, day_end))\
            .scalar() or 0
            
        values.append(round(day_income, 2))
    
    return {
        'labels': labels,
        'values': values
    }

@admin_api_bp.route('/income-list')
@admin_required
def get_income_list():
    """获取平台收入明细"""
    try:
        # 获取查询参数
        period = request.args.get('period', 'today')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # 当前日期时间
        now = datetime.utcnow()
        today = now.date()
        
        # 构建查询条件
        query = db.session.query(
            DBPlatformIncome.id,
            DBPlatformIncome.type,
            DBPlatformIncome.amount,
            literal('USDC').label('currency'),
            DBPlatformIncome.created_at,
            DBPlatformIncome.description,
            DBPlatformIncome.tx_hash.label('transaction_hash'),
            DBPlatformIncome.asset_id,
            Asset.name.label('asset_name'),
            Asset.token_symbol.label('asset_symbol')
        ).outerjoin(Asset, DBPlatformIncome.asset_id == Asset.id)
        
        # 根据时间筛选
        if period == 'today':
            day_start = datetime.combine(today, datetime.min.time())
            day_end = datetime.combine(today, datetime.max.time())
            query = query.filter(DBPlatformIncome.created_at.between(day_start, day_end))
            
        elif period == 'week':
            # 本周开始（周一）
            week_start = today - timedelta(days=today.weekday())
            week_start = datetime.combine(week_start, datetime.min.time())
            query = query.filter(DBPlatformIncome.created_at >= week_start)
            
        elif period == 'month':
            # 本月开始
            month_start = today.replace(day=1)
            month_start = datetime.combine(month_start, datetime.min.time())
            query = query.filter(DBPlatformIncome.created_at >= month_start)
            
        elif period == 'year':
            # 本年开始
            year_start = today.replace(month=1, day=1)
            year_start = datetime.combine(year_start, datetime.min.time())
            query = query.filter(DBPlatformIncome.created_at >= year_start)
        
        # 按时间降序排序
        query = query.order_by(DBPlatformIncome.created_at.desc())
        
        # 获取总记录数和总金额
        total_records = query.count()
        total_amount = db.session.query(func.sum(DBPlatformIncome.amount))\
            .filter(DBPlatformIncome.id.in_([item.id for item in query]))\
            .scalar() or 0
        
        # 计算总页数
        total_pages = (total_records + per_page - 1) // per_page
        
        # 分页
        items = query.limit(per_page).offset((page - 1) * per_page).all()
        
        # 转换为JSON格式
        income_list = []
        for item in items:
            income_data = {
                'id': item.id,
                'income_type': item.type,
                'income_type_text': get_income_type_text(item.type),
                'amount': round(item.amount, 6),
                'currency': item.currency,
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'description': item.description,
                'transaction_hash': item.transaction_hash,
                'asset_id': item.asset_id,
                'asset_name': item.asset_name or '未关联资产',
                'asset_symbol': item.asset_symbol or '--'
            }
            income_list.append(income_data)
        
        # 如果没有数据，返回空列表
        if not income_list and page == 1:
            return jsonify({
                'total_records': 0,
                'total_pages': 0,
                'current_page': 1,
                'total_amount': 0,
                'income_list': []
            })
        
        return jsonify({
            'total_records': total_records,
            'total_pages': total_pages,
            'current_page': page,
            'total_amount': round(total_amount, 6),
            'income_list': income_list
        })
        
    except Exception as e:
        current_app.logger.error(f'获取平台收入明细失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取平台收入明细失败',
            'message': str(e)
        }), 500

def get_income_type_text(income_type):
    """获取收入类型的中文名称"""
    income_type_map = {
        IncomeType.ASSET_ONCHAIN.value: '链上服务费',
        IncomeType.TRANSACTION.value: '交易手续费',
        IncomeType.DIVIDEND.value: '分红手续费',
        IncomeType.OTHER.value: '其他收入'
    }
    return income_type_map.get(income_type, '未知类型')

@admin_api_bp.route('/update-fees', methods=['POST'])
@admin_required
def update_fees():
    """更新平台费率设置"""
    try:
        current_app.logger.info('更新平台费率设置...')
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据无效'}), 400
        
        # 验证必要字段
        required_fields = [
            'standard_fee', 'large_fee', 'self_fee', 
            'large_threshold', 'onchain_fee', 'min_onchain_fee', 
            'dividend_fee', 'contract_fee'
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'缺少必要字段: {field}'}), 400
        
        # 验证值范围
        if not (0 <= float(data['standard_fee']) <= 1):
            return jsonify({'error': '标准交易费率应在0-1%范围内'}), 400
        
        if not (0 <= float(data['large_fee']) <= 0.5):
            return jsonify({'error': '大额交易费率应在0-0.5%范围内'}), 400
        
        if not (0 <= float(data['self_fee']) <= 0.3):
            return jsonify({'error': '自持交易费率应在0-0.3%范围内'}), 400
        
        if not (1000 <= int(data['large_threshold']) <= 100000):
            return jsonify({'error': '大额交易阈值应在1,000-100,000范围内'}), 400
        
        if not (0.0001 <= float(data['onchain_fee']) <= 10):
            return jsonify({'error': '上链费率应在0.0001-10范围内'}), 400
        
        if not (10 <= int(data['min_onchain_fee']) <= 1000):
            return jsonify({'error': '最低上链费用应在10-1,000范围内'}), 400
        
        if not (0.1 <= float(data['dividend_fee']) <= 5):
            return jsonify({'error': '分红手续费率应在0.1%-5%范围内'}), 400
        
        if not (0.1 <= float(data['contract_fee']) <= 5):
            return jsonify({'error': '智能合约费率应在0.1%-5%范围内'}), 400
        
        # 保存费率设置到系统配置表
        save_fee_settings(data)
        
        current_app.logger.info('平台费率设置已更新')
        return jsonify({'success': True, 'message': '费率设置已更新'})
        
    except Exception as e:
        current_app.logger.error(f'更新平台费率设置失败: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

def get_current_fee_settings():
    """获取当前费率设置"""
    # 这里应该从系统配置表中读取，现在暂时返回默认值
    return {
        "standard_fee": 0.5,  # 0.5%
        "large_fee": 0.3,     # 0.3%
        "self_fee": 0.1,      # 0.1%
        "large_threshold": 10000,     # 10,000 USDC
        "onchain_fee": 1,        # 万分之一，前端会除以100显示为0.01%
        "min_onchain_fee": 100,       # 100 USDC
        "dividend_fee": 1,         # 1%
        "contract_fee": 2.5,        # 2.5%
        "promotion": {
            "enabled": False,
            "start_date": datetime.utcnow().date().isoformat(),
            "end_date": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
            "description": "七日促销",
            "trade_discount": 20,     # 20%折扣
            "onchain_discount": 15    # 15%折扣
        }
    }

def save_fee_settings(settings):
    """保存费率设置"""
    # 这里应该将设置保存到系统配置表中
    # 现在暂时只打印日志
    current_app.logger.info(f'保存费率设置: {settings}')
    
    # TODO: 保存到数据库系统配置表
    
    # 在实际应用中，我们可以使用以下SQL创建配置表：
    # CREATE TABLE system_settings (
    #     key VARCHAR(50) PRIMARY KEY,
    #     value TEXT NOT NULL,
    #     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    # ); 

@admin_api_bp.route('/asset-type-stats')
def get_asset_type_stats():
    """获取资产类型分布统计"""
    try:
        # 检查是否提供了钱包地址
        eth_address = None
        if 'X-Eth-Address' in request.headers:
            eth_address = request.headers.get('X-Eth-Address')
        if not eth_address and 'eth_address' in request.cookies:
            eth_address = request.cookies.get('eth_address')
        if not eth_address and 'eth_address' in session:
            eth_address = session.get('eth_address')
        if not eth_address and 'admin_eth_address' in session:
            eth_address = session.get('admin_eth_address')
            
        # 记录请求
        current_app.logger.info(f"访问资产类型统计API，地址: {eth_address}")
        
        # 查询资产类型分布
        distribution = db.session.query(
            Asset.asset_type,
            func.count(Asset.id).label('count'),
            func.sum(Asset.total_value).label('value')
        ).group_by(Asset.asset_type).all()
        
        result = []
        
        # 类型名称映射
        asset_type_names = {
            10: '不动产',
            20: '类不动产',
            30: '工业地产',
            40: '土地资产',
            50: '证券资产',
            60: '艺术品',
            70: '收藏品'
        }
        
        # 类型颜色映射
        asset_type_colors = {
            10: '#4e73df',  # 蓝色
            20: '#1cc88a',  # 绿色
            30: '#36b9cc',  # 青色
            40: '#f6c23e',  # 黄色
            50: '#e74a3b',  # 红色
            60: '#6f42c1',  # 紫色
            70: '#fd7e14',  # 橙色
        }
        
        for type_id, count, value in distribution:
            result.append({
                'id': type_id,
                'type': type_id,
                'name': asset_type_names.get(type_id, f'类型{type_id}'),
                'count': count,
                'value': float(value) if value else 0,
                'color': asset_type_colors.get(type_id, '#858796')  # 灰色为默认
            })
            
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"获取资产类型分布统计失败: {str(e)}", exc_info=True)
        return jsonify([])

@admin_api_bp.route('/user-growth')
@admin_required
def get_user_growth():
    """获取用户增长趋势数据"""
    try:
        current_app.logger.info('获取用户增长趋势数据...')
        
        # 获取周期参数
        period = request.args.get('period', 'daily')
        
        # 当前日期
        today = datetime.utcnow().date()
        
        labels = []
        values = []
        
        # 根据周期生成不同的日期范围和格式
        if period == 'daily':
            # 过去7天的数据
            for i in range(6, -1, -1):
                date = today - timedelta(days=i)
                date_str = date.strftime('%m-%d')
                labels.append(date_str)
                
                # 统计该日期创建的用户数量
                start_date = datetime.combine(date, datetime.min.time())
                end_date = datetime.combine(date, datetime.max.time())
                
                count = db.session.query(db.func.count(db.func.distinct(Asset.owner_address)))\
                    .filter(Asset.created_at.between(start_date, end_date))\
                    .scalar() or 0
                
                values.append(count)
                
        elif period == 'monthly':
            # 过去12个月的数据
            for i in range(11, -1, -1):
                # 计算月份
                year = today.year
                month = today.month - i
                
                if month <= 0:
                    month += 12
                    year -= 1
                
                # 构建月份的起止日期
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
                end_date = datetime.combine(end_date, datetime.max.time())
                
                # 月份标签
                date_str = start_date.strftime('%Y-%m')
                labels.append(date_str)
                
                # 统计该月创建的用户数量
                count = db.session.query(db.func.count(db.func.distinct(Asset.owner_address)))\
                    .filter(Asset.created_at.between(start_date, end_date))\
                    .scalar() or 0
                
                values.append(count)
        
        # 如果没有数据，返回一个有意义的默认值
        if not labels or sum(values) == 0:
            if period == 'daily':
                labels = [date.strftime('%m-%d') for date in [(today - timedelta(days=i)) for i in range(6, -1, -1)]]
                values = [0] * 7
            else:
                labels = ['暂无数据']
                values = [0]
        
        return jsonify({
            'labels': labels,
            'values': values
        })
        
    except Exception as e:
        current_app.logger.error(f'获取用户增长趋势数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取用户增长趋势数据失败',
            'message': str(e)
        }), 500

@admin_api_bp.route('/user-stats', methods=['GET'])
def get_user_stats():
    """获取用户统计数据"""
    try:
        # 检查是否提供了钱包地址
        eth_address = None
        if 'X-Eth-Address' in request.headers:
            eth_address = request.headers.get('X-Eth-Address')
        if not eth_address and 'eth_address' in request.cookies:
            eth_address = request.cookies.get('eth_address')
        if not eth_address and 'eth_address' in session:
            eth_address = session.get('eth_address')
        if not eth_address and 'admin_eth_address' in session:
            eth_address = session.get('admin_eth_address')
            
        # 记录请求
        current_app.logger.info(f"访问用户统计API，地址: {eth_address}, 参数: {request.args}")
        
        # 获取传入的时间周期参数
        period = request.args.get('period', 'weekly')
        
        # 当前日期时间
        now = datetime.utcnow()
        today = now.date()
        
        # 返回数据格式调整为前端期望的格式
        result = []
        
        if period == 'weekly':
            # 获取最近7天的数据
            for i in range(6, -1, -1):
                day_date = today - timedelta(days=i)
                day_start = datetime.combine(day_date, datetime.min.time())
                day_end = datetime.combine(day_date, datetime.max.time())
                
                # 日期标签
                day_label = day_date.strftime('%m-%d')
                
                # 新注册用户数
                new_user_count = db.session.query(db.func.count(User.id))\
                    .filter(User.created_at.between(day_start, day_end))\
                    .scalar() or 0
                
                # 活跃用户数（以交易或查看资产作为活跃指标）
                # 修复：使用trader_address替代不存在的user_id
                active_trade_users = db.session.query(db.func.count(db.distinct(Trade.trader_address)))\
                    .filter(Trade.created_at.between(day_start, day_end))\
                    .scalar() or 0
                
                # 统计当天有资产查看记录的用户数量
                # 为简化，这里仅以资产创建者作为访问记录替代
                active_asset_users = db.session.query(db.func.count(db.distinct(Asset.creator_address)))\
                    .filter(Asset.updated_at.between(day_start, day_end))\
                    .scalar() or 0
                
                # 合并去重
                active_user_count = active_trade_users + active_asset_users
                
                # 添加当天数据
                result.append({
                    'date': day_label,
                    'new_users': new_user_count,
                    'active_users': active_user_count
                })
        elif period == 'monthly':
            # 获取最近30天的数据，按周汇总
            for week in range(4, 0, -1):
                week_end = today - timedelta(days=(week-1)*7)
                week_start = week_end - timedelta(days=6)
                
                # 日期标签
                week_label = f"{week_start.strftime('%m-%d')} ~ {week_end.strftime('%m-%d')}"
                
                # 周开始和结束时间
                week_start_dt = datetime.combine(week_start, datetime.min.time())
                week_end_dt = datetime.combine(week_end, datetime.max.time())
                
                # 新注册用户数
                new_user_count = db.session.query(db.func.count(User.id))\
                    .filter(User.created_at.between(week_start_dt, week_end_dt))\
                    .scalar() or 0
                
                # 活跃用户数
                active_trade_users = db.session.query(db.func.count(db.distinct(Trade.trader_address)))\
                    .filter(Trade.created_at.between(week_start_dt, week_end_dt))\
                    .scalar() or 0
                
                active_asset_users = db.session.query(db.func.count(db.distinct(Asset.creator_address)))\
                    .filter(Asset.updated_at.between(week_start_dt, week_end_dt))\
                    .scalar() or 0
                
                active_user_count = active_trade_users + active_asset_users
                
                # 添加当周数据
                result.append({
                    'date': week_label,
                    'new_users': new_user_count,
                    'active_users': active_user_count
                })
                
        elif period == 'yearly':
            # 获取最近12个月的数据
            for month in range(11, -1, -1):
                month_date = today.replace(day=1) - timedelta(days=month*30)
                month_end = month_date.replace(day=calendar.monthrange(month_date.year, month_date.month)[1])
                
                # 月份标签
                month_label = month_date.strftime('%Y-%m')
                
                # 月开始和结束时间
                month_start_dt = datetime.combine(month_date.replace(day=1), datetime.min.time())
                month_end_dt = datetime.combine(month_end, datetime.max.time())
                
                # 新注册用户数
                new_user_count = db.session.query(db.func.count(User.id))\
                    .filter(User.created_at.between(month_start_dt, month_end_dt))\
                    .scalar() or 0
                
                # 活跃用户数
                active_trade_users = db.session.query(db.func.count(db.distinct(Trade.trader_address)))\
                    .filter(Trade.created_at.between(month_start_dt, month_end_dt))\
                    .scalar() or 0
                
                active_asset_users = db.session.query(db.func.count(db.distinct(Asset.creator_address)))\
                    .filter(Asset.updated_at.between(month_start_dt, month_end_dt))\
                    .scalar() or 0
                
                active_user_count = active_trade_users + active_asset_users
                
                # 添加当月数据
                result.append({
                    'date': month_label,
                    'new_users': new_user_count,
                    'active_users': active_user_count
                })
        
        # 获取用户地理分布（假数据，实际应从用户IP或注册信息中获取）
        regions = [
            {'name': '中国', 'value': 60},
            {'name': '美国', 'value': 20},
            {'name': '欧洲', 'value': 15},
            {'name': '其他', 'value': 5}
        ]
        
        return jsonify({
            'trend': result,
            'regions': regions
        })
        
    except Exception as e:
        current_app.logger.error(f"获取用户统计失败: {str(e)}", exc_info=True)
        return jsonify({
            'trend': [],
            'regions': []
        })

@admin_api_bp.route('/billing/list', methods=['GET'])
def get_billing_list():
    """获取账单列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        
        # 获取过滤条件
        status = request.args.get('status')
        billing_type = request.args.get('type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # 构建查询
        query = db.session.query(DBPlatformIncome)
        
        # 应用过滤条件
        if status:
            # 在描述中查找状态
            query = query.filter(DBPlatformIncome.description.like(f'%[状态:{status}]%'))
        if billing_type:
            if billing_type == 'trade_fee':
                query = query.filter(DBPlatformIncome.type == IncomeType.TRANSACTION.value)
            elif billing_type == 'onchain_fee':
                query = query.filter(DBPlatformIncome.type == IncomeType.ASSET_ONCHAIN.value)
            elif billing_type == 'dividend_fee':
                query = query.filter(DBPlatformIncome.type == IncomeType.DIVIDEND.value)
        if date_from:
            query = query.filter(DBPlatformIncome.created_at >= date_from)
        if date_to:
            query = query.filter(DBPlatformIncome.created_at <= date_to)
        
        # 分页处理
        pagination = query.order_by(DBPlatformIncome.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )
        
        # 格式化数据
        records = []
        for item in pagination.items:
            # 映射income_type到前端需要的type
            income_type_mapping = {
                IncomeType.TRANSACTION.value: 'trade_fee',
                IncomeType.ASSET_ONCHAIN.value: 'onchain_fee',
                IncomeType.DIVIDEND.value: 'dividend_fee',
                IncomeType.OTHER.value: 'other'
            }
            
            # 提取状态信息 - 从描述中解析
            status = 'pending'  # 默认状态
            if item.description and '[状态:' in item.description:
                status_match = re.search(r'\[状态:([^\]]+)\]', item.description)
                if status_match:
                    status = status_match.group(1)
            
            income_type = income_type_mapping.get(item.type, 'other')
            
            # 获取用户钱包地址（如果有关联）
            # 这里需要处理未关联用户的情况
            user_id = None
            wallet_address = '-'
            
            # 构建记录
            records.append({
                "id": item.id,
                "bill_no": f"B{item.id:08d}",
                "type": income_type,
                "amount": str(item.amount),
                "currency": "USDC",
                "status": status,
                "created_at": item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "asset_id": item.asset_id,
                "asset_name": item.asset.name if hasattr(item, 'asset') and item.asset else "未知资产",
                "user_id": user_id,
                "wallet_address": wallet_address
            })
        
        return jsonify({
            "total": pagination.total,
            "page": page,
            "page_size": page_size,
            "total_pages": pagination.pages,
            "records": records
        })
    
    except Exception as e:
        current_app.logger.error(f'获取账单列表失败: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/billing/stats', methods=['GET'])
def get_billing_stats():
    """获取账单统计信息"""
    try:
        # 获取今日账单总额
        today = get_utc_today()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        
        today_total = db.session.query(func.sum(DBPlatformIncome.amount)).filter(
            DBPlatformIncome.created_at.between(today_start, today_end)
        ).scalar() or 0
        
        # 获取本月账单总额
        month_start = datetime(today.year, today.month, 1)
        month_end = datetime.combine(today, time.max)
        
        month_total = db.session.query(func.sum(DBPlatformIncome.amount)).filter(
            DBPlatformIncome.created_at.between(month_start, month_end)
        ).scalar() or 0
        
        # 获取总账单金额
        all_time_total = db.session.query(func.sum(DBPlatformIncome.amount)).scalar() or 0
        
        # 获取不同类型账单的分布
        type_distribution = db.session.query(
            DBPlatformIncome.type,
            func.sum(DBPlatformIncome.amount)
        ).group_by(
            DBPlatformIncome.type
        ).all()
        
        type_data = {}
        income_type_mapping = {
            IncomeType.TRANSACTION.value: 'trade_fee',
            IncomeType.ASSET_ONCHAIN.value: 'onchain_fee',
            IncomeType.DIVIDEND.value: 'dividend_fee',
            IncomeType.OTHER.value: 'other'
        }
        
        for income_type, amount in type_distribution:
            type_key = income_type_mapping.get(income_type, 'other')
            type_data[type_key] = str(amount)
        
        # 获取近30天的账单趋势
        trend_data = []
        for i in range(30, 0, -1):
            date = today - timedelta(days=i-1)
            date_start = datetime.combine(date, time.min)
            date_end = datetime.combine(date, time.max)
            
            daily_amount = db.session.query(func.sum(DBPlatformIncome.amount)).filter(
                DBPlatformIncome.created_at.between(date_start, date_end)
            ).scalar() or 0
            
            trend_data.append({
                "date": date.strftime('%m-%d'),
                "amount": str(daily_amount)
            })
        
        return jsonify({
            "today_total": str(today_total),
            "month_total": str(month_total),
            "all_time_total": str(all_time_total),
            "type_distribution": type_data,
            "trend": trend_data
        })
    
    except Exception as e:
        current_app.logger.error(f'获取账单统计信息失败: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/billing/update', methods=['POST'])
def update_billing_status():
    """更新账单状态"""
    try:
        data = request.get_json()
        
        if not data or 'id' not in data or 'status' not in data:
            return jsonify({'error': '缺少必要的参数'}), 400
        
        billing_id = data['id']
        new_status = data['status']
        
        # 验证状态是否有效
        if new_status not in ['pending', 'processing', 'completed', 'failed', 'cancelled']:
            return jsonify({'error': '无效的状态值'}), 400
        
        # 查找账单
        billing = DBPlatformIncome.query.get(billing_id)
        if not billing:
            return jsonify({'error': '账单不存在'}), 404
        
        # 在描述字段中记录状态信息
        status_text = f"[状态:{new_status}]"
        if billing.description:
            if "[状态:" in billing.description:
                billing.description = re.sub(r'\[状态:[^\]]+\]', status_text, billing.description)
            else:
                billing.description = f"{billing.description} {status_text}"
        else:
            billing.description = status_text
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '账单状态已更新',
            'billing': {
                'id': billing.id,
                'status': new_status,
                'updated_at': billing.updated_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(billing, 'updated_at') and billing.updated_at else None
            }
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'更新账单状态失败: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500 

@admin_bp.route('/v2/dashboard')
@admin_required
def dashboard_v2():
    """管理后台V2版本仪表板"""
    return render_template('admin_v2/dashboard.html')

@admin_bp.route('/v2/users')
@admin_required
def users_v2():
    """管理后台V2版本用户管理页面"""
    return render_template('admin_v2/users.html')

@admin_bp.route('/v2/assets')
def assets_v2():
    """V2资产管理页面"""
    return render_template('admin_v2/assets.html')

@admin_bp.route('/v2/commission')
@admin_required
def commission_v2():
    """管理后台V2版本佣金管理页面"""
    return render_template('admin_v2/commission.html')

@admin_bp.route('/v2/trades')
@admin_required
def trades_v2():
    """管理后台V2版本交易管理页面"""
    return render_template('admin_v2/trades.html')

@admin_bp.route('/v2/settings', methods=['GET', 'POST'])
@admin_required # 使用页面权限装饰器
@permission_required('管理设置') # 假设需要 '管理设置' 权限
def settings_v2():
    """管理后台V2版本系统设置页面，包含支付相关配置"""
    required_configs = [
        'PLATFORM_FEE_BASIS_POINTS', 
        'PLATFORM_FEE_ADDRESS', 
        'PURCHASE_CONTRACT_ADDRESS', 
        'ASSET_CREATION_FEE_AMOUNT', 
        'ASSET_CREATION_FEE_ADDRESS'
    ]
    
    if request.method == 'POST':
        try:
            # 获取并验证表单数据
            config_updates = {}
            errors = {}

            # 平台购买费率 (Basis Points)
            fee_basis_points = request.form.get('platform_fee_basis_points')
            try:
                val = int(fee_basis_points)
                if 0 <= val <= 10000: # 0% to 100%
                    config_updates['PLATFORM_FEE_BASIS_POINTS'] = str(val)
                else:
                    errors['platform_fee_basis_points'] = '费率基点必须在 0 到 10000 之间'
            except (ValueError, TypeError):
                errors['platform_fee_basis_points'] = '费率基点必须是有效的整数'
            
            # 平台购买收款地址 (Solana)
            fee_address = request.form.get('platform_fee_address')
            if fee_address and is_valid_solana_address(fee_address):
                config_updates['PLATFORM_FEE_ADDRESS'] = fee_address
            elif fee_address:
                errors['platform_fee_address'] = '平台购买收款地址格式无效 (Solana)'
            else:
                errors['platform_fee_address'] = '平台购买收款地址不能为空' # 必须配置

            # 购买智能合约地址 (Solana)
            contract_address = request.form.get('purchase_contract_address')
            if contract_address and is_valid_solana_address(contract_address):
                config_updates['PURCHASE_CONTRACT_ADDRESS'] = contract_address
            elif contract_address:
                errors['purchase_contract_address'] = '购买智能合约地址格式无效 (Solana)'
            else:
                 errors['purchase_contract_address'] = '购买智能合约地址不能为空' # 必须配置

            # 资产创建费用金额 (USDC)
            creation_fee = request.form.get('asset_creation_fee_amount')
            try:
                val = Decimal(creation_fee)
                if val >= 0:
                    config_updates['ASSET_CREATION_FEE_AMOUNT'] = str(val.quantize(Decimal('0.000001')))
                else:
                    errors['asset_creation_fee_amount'] = '创建费用金额不能为负数'
            except (ValueError, TypeError):
                errors['asset_creation_fee_amount'] = '创建费用金额必须是有效的数字'
            
            # 资产创建收款地址 (Solana)
            creation_address = request.form.get('asset_creation_fee_address')
            if creation_address and is_valid_solana_address(creation_address):
                config_updates['ASSET_CREATION_FEE_ADDRESS'] = creation_address
            elif creation_address:
                errors['asset_creation_fee_address'] = '创建费用收款地址格式无效 (Solana)'
            else:
                 errors['asset_creation_fee_address'] = '创建费用收款地址不能为空' # 必须配置

            if errors:
                for field, msg in errors.items():
                    flash(f'{field}: {msg}', 'error')
            else:
                # 保存配置到数据库
                for key, value in config_updates.items():
                    SystemConfig.set_value(key, value, description=f'System setting for {key}')
                flash('系统设置已成功更新', 'success')
                current_app.logger.info(f"管理员 {g.eth_address} 更新了系统设置: {config_updates.keys()}")
                # 更新配置后最好重新加载或清除缓存（如果应用有缓存配置）
                # current_app.config.update(SystemConfig.load_all_to_dict()) # 示例：如果配置缓存在 app.config

            # 无论成功或失败，都重定向回 GET 请求，以显示更新后的值或错误
            return redirect(url_for('admin.settings_v2'))
            
        except Exception as e:
            current_app.logger.error(f"更新系统设置失败: {str(e)}", exc_info=True)
            flash('更新设置时发生内部错误', 'error')
            return redirect(url_for('admin.settings_v2'))

    # 处理 GET 请求
    configs = {}
    # 提供默认值，避免后端 API 因配置缺失而出错
    default_values = {
        'PLATFORM_FEE_BASIS_POINTS': '350', # 3.5%
        'PLATFORM_FEE_ADDRESS': '', # 必须配置
        'PURCHASE_CONTRACT_ADDRESS': '', # 必须配置
        'ASSET_CREATION_FEE_AMOUNT': '1.0', # 1 USDC
        'ASSET_CREATION_FEE_ADDRESS': '' # 必须配置
    }
    for key in required_configs:
        configs[key] = SystemConfig.get_value(key, default=default_values.get(key, ''))
        
    return render_template('admin_v2/settings.html', configs=configs)

@admin_bp.route('/v2/admin-users')
@admin_required
def admin_users_v2():
    """管理后台V2版本管理员用户页面"""
    return render_template('admin_v2/admin_users.html')

@admin_bp.route('/v2/login')
def login_v2():
    """管理后台V2版本登录页面"""
    return render_template('admin_v2/login.html')

@admin_bp.route('/v2')
@admin_required
def admin_v2_index():
    """管理后台V2版本首页"""
    admin = None
    eth_address = request.headers.get('X-Eth-Address') or request.cookies.get('eth_address') or session.get('eth_address')
    
    if eth_address:
        # 尝试从新管理员表中获取信息
        admin = AdminUser.query.filter_by(wallet_address=eth_address).first()
        
        # 如果在新表中没有找到，则使用旧配置
        if not admin and eth_address in current_app.config['ADMIN_CONFIG']:
            admin = {'wallet_address': eth_address}
    
    if not admin:
        return redirect(url_for('admin.login'))
    
    return render_template('admin_v2/index.html', admin=admin)

@admin_bp.route('/v2/api/check-auth')
def check_auth_v2():
    """检查管理员认证状态V2"""
    try:
        current_app.logger.info("收到管理员认证检查请求，请求头信息：%s", request.headers)
        wallet_address = None
        
        # 尝试从多个来源获取钱包地址
        if 'Wallet-Address' in request.headers:
            wallet_address = request.headers.get('Wallet-Address')
            current_app.logger.info("从请求头中获取到钱包地址: %s", wallet_address)
        elif request.cookies.get('wallet_address'):
            wallet_address = request.cookies.get('wallet_address')
            current_app.logger.info("从cookies中获取到钱包地址: %s", wallet_address)
        elif session.get('wallet_address'):
            wallet_address = session.get('wallet_address')
            current_app.logger.info("从session中获取到钱包地址: %s", wallet_address)
        
        if not wallet_address:
            current_app.logger.warning("未找到钱包地址，认证失败")
            return jsonify({
                'authenticated': False,
                'message': '未找到钱包地址，请重新登录'
            }), 401
        
        # 查询管理员用户
        admin_user = AdminUser.query.filter_by(wallet_address=wallet_address).first()
        
        if admin_user:
            current_app.logger.info("管理员认证成功: %s", wallet_address)
            return jsonify({
                'authenticated': True,
                'wallet_address': wallet_address,
                'admin_level': admin_user.admin_level,
                'message': '认证成功'
            })
        else:
            current_app.logger.warning("管理员认证失败，钱包地址不在管理员列表中: %s", wallet_address)
            return jsonify({
                'authenticated': False,
                'message': '您不是管理员，无法访问'
            }), 403
    except Exception as e:
        current_app.logger.error("管理员认证检查过程中发生错误: %s", str(e), exc_info=True)
        return jsonify({
            'authenticated': False,
            'message': '认证过程中发生错误',
            'error': str(e)
        }), 500

@admin_bp.route('/v2/api/logout', methods=['POST'])
def logout_v2():
    """管理员退出登录"""
    session.pop('eth_address', None)
    response = jsonify({'success': True})
    response.delete_cookie('eth_address')
    return response

@admin_bp.route('/v2/api/assets', methods=['GET'])
def api_assets_v2():
    """管理后台V2版本资产列表API"""
    try:
        # 记录请求信息，方便调试
        current_app.logger.info(f"访问V2资产列表API，参数: {request.args}")
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # 查询资产列表 - 管理后台始终显示所有未删除的资产
        query = Asset.query.filter(Asset.status != 0)  # 0 表示已删除
        
        # 查询筛选条件
        status = request.args.get('status')
        asset_type = request.args.get('type')
        keyword = request.args.get('keyword')
        
        if status:
            query = query.filter(Asset.status == int(status))
        
        if asset_type:
            query = query.filter(Asset.asset_type == int(asset_type))
            
        if keyword:
            query = query.filter(
                or_(
                    Asset.name.ilike(f'%{keyword}%'),
                    Asset.description.ilike(f'%{keyword}%'),
                    Asset.token_symbol.ilike(f'%{keyword}%')
                )
            )
        
        # 排序
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')
        
        if sort_order == 'desc':
            query = query.order_by(desc(getattr(Asset, sort_field)))
        else:
            query = query.order_by(getattr(Asset, sort_field))
        
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        assets = pagination.items
        
        current_app.logger.info(f"查询到 {len(assets)} 个资产，总计 {pagination.total} 个")
        
        # 格式化返回数据
        asset_list = []
        for asset in assets:
            try:
                # 获取资产类型名称
                asset_type_name = '未知类型'
                asset_type_value = asset.asset_type
                
                # 尝试查找枚举值
                for item in AssetType:
                    if item.value == asset_type_value:
                        asset_type_name = item.name
                        break
                
                # 获取封面图片  
                cover_image = '/static/images/placeholder.jpg'
                if asset.images and len(asset.images) > 0:
                    cover_image = asset.images[0]
                        
                asset_list.append({
                    'id': asset.id,
                    'name': asset.name,
                    'token_symbol': asset.token_symbol,
                    'asset_type': asset.asset_type,
                    'asset_type_name': asset_type_name,
                    'location': asset.location,
                    'area': float(asset.area) if asset.area else 0,
                    'token_price': float(asset.token_price) if asset.token_price else 0,
                    'annual_revenue': float(asset.annual_revenue) if asset.annual_revenue else 0,
                    'total_value': float(asset.total_value) if asset.total_value else 0,
                    'token_supply': asset.token_supply,
                    'creator_address': asset.creator_address,
                    'status': asset.status,
                    'status_text': {
                        1: '待审核',
                        2: '已通过',
                        3: '已拒绝',
                        4: '已删除'
                    }.get(asset.status, '未知状态'),
                    'image': cover_image,
                    'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else None
                })
            except Exception as item_error:
                current_app.logger.error(f"处理资产 {asset.id} 数据失败: {str(item_error)}")
                # 继续处理下一个资产
        
        return jsonify({
            'items': asset_list,
            'total': pagination.total,
            'page': page,
            'limit': limit,
            'pages': pagination.pages
        })
    except Exception as e:
        current_app.logger.error(f"获取资产列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'items': [],
            'total': 0,
            'page': 1,
            'limit': 10,
            'pages': 0
        })

@admin_bp.route('/v2/api/assets/stats', methods=['GET'])
def api_assets_stats_v2():
    """管理后台V2版本资产统计API"""
    try:
        # 统计数据
        total_assets = Asset.query.filter(Asset.status != 0).count()
        pending_assets = Asset.query.filter(Asset.status == 1).count()
        approved_assets = Asset.query.filter(Asset.status == 2).count()
        rejected_assets = Asset.query.filter(Asset.status == 3).count()
        
        # 总价值 (只统计已审核通过的资产)
        total_value = db.session.query(func.sum(Asset.total_value)).filter(Asset.status == 2).scalar() or 0
        
        # 资产类型分布
        asset_types = {}
        for asset_type in AssetType:
            count = Asset.query.filter(Asset.asset_type == asset_type.value).count()
            if count > 0:
                asset_types[asset_type.name] = count
        
        # 状态分布
        status_distribution = {
            'pending': pending_assets,
            'approved': approved_assets,
            'rejected': rejected_assets
        }
        
        # 返回统计数据
        return jsonify({
            'totalAssets': total_assets,
            'totalValue': float(total_value),
            'pendingAssets': pending_assets,
            'assetTypes': len(asset_types),
            'type_distribution': asset_types,
            'status_distribution': status_distribution
        })
    except Exception as e:
        current_app.logger.error(f"获取资产统计失败: {str(e)}", exc_info=True)
        return jsonify({
            'totalAssets': 0,
            'totalValue': 0,
            'pendingAssets': 0,
            'assetTypes': 0,
            'type_distribution': {},
            'status_distribution': {}
        })

@admin_bp.route('/v2/api/assets/<int:asset_id>', methods=['PUT'])
@api_admin_required
def api_edit_asset_v2(asset_id):
    """管理后台V2版本编辑资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '资产更新成功'})

@admin_bp.route('/v2/api/assets', methods=['POST'])
@api_admin_required
def api_create_asset_v2():
    """管理后台V2版本创建资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '资产创建成功', 'id': 100})

@admin_bp.route('/v2/api/assets/<int:asset_id>', methods=['DELETE'])
@api_admin_required
def api_delete_asset_v2(asset_id):
    """管理后台V2版本删除资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '资产删除成功'})

@admin_bp.route('/v2/api/assets/<int:asset_id>/approve', methods=['POST'])
@api_admin_required
def api_approve_asset_v2(asset_id):
    """管理后台V2版本批准资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '资产批准成功'})

@admin_bp.route('/v2/api/assets/<int:asset_id>/reject', methods=['POST'])
@api_admin_required
def api_reject_asset_v2(asset_id):
    """管理后台V2版本拒绝资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '资产拒绝成功'})

@admin_bp.route('/v2/api/assets/batch-approve', methods=['POST'])
@api_admin_required
def api_batch_approve_assets_v2():
    """管理后台V2版本批量批准资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '批量批准资产成功'})

@admin_bp.route('/v2/api/assets/batch-reject', methods=['POST'])
@api_admin_required
def api_batch_reject_assets_v2():
    """管理后台V2版本批量拒绝资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '批量拒绝资产成功'})

@admin_bp.route('/v2/api/assets/batch-delete', methods=['POST'])
@api_admin_required
def api_batch_delete_assets_v2():
    """管理后台V2版本批量删除资产API"""
    # 模拟成功响应
    return jsonify({'success': True, 'message': '批量删除资产成功'})

@admin_bp.route('/v2/api/assets/export', methods=['GET'])
@api_admin_required
def api_export_assets_v2():
    """管理后台V2版本导出资产API"""
    # 在实际实现中，这里应该返回一个CSV或Excel文件
    # 为了演示，我们只返回一个文本响应
    return "资产导出功能正在开发中", 200, {'Content-Type': 'text/plain'}

@admin_bp.route('/v2/api/dashboard/stats', methods=['GET'])
def api_dashboard_stats_v2():
    """获取仪表盘统计数据"""
    try:
        # 获取用户统计
        total_users = User.query.count()
        new_users_today = User.query.filter(
            func.date(User.created_at) == func.date(datetime.now())
        ).count()
        
        # 获取资产统计
        total_assets = Asset.query.filter(Asset.status != 0).count()
        total_asset_value = db.session.query(func.sum(Asset.total_value)).filter(
            Asset.status == 2  # 只统计已审核通过的资产
        ).scalar() or 0
        
        # 获取交易统计
        total_trades = Trade.query.count()
        total_trade_volume = db.session.query(func.sum(Trade.total_price)).scalar() or 0
        
        return jsonify({
            'total_users': total_users,
            'new_users_today': new_users_today,
            'total_assets': total_assets,
            'total_asset_value': float(total_asset_value),
            'total_trades': total_trades,
            'total_trade_volume': float(total_trade_volume)
        })
        
    except Exception as e:
        current_app.logger.error(f'获取仪表盘统计数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'total_users': 0,
            'new_users_today': 0,
            'total_assets': 0,
            'total_asset_value': 0,
            'total_trades': 0,
            'total_trade_volume': 0
        })

@admin_bp.route('/v2/api/dashboard/trends', methods=['GET'])
def api_dashboard_trends_v2():
    """获取仪表盘趋势数据"""
    try:
        days = int(request.args.get('days', 30))
        if days not in [7, 30, 90]:
            days = 30
            
        # 获取用户增长趋势
        user_growth = get_user_growth_trend(days)
        
        # 获取交易量趋势
        trading_volume = get_trading_volume_trend(days)
        
        return jsonify({
            'user_growth': user_growth,
            'trading_volume': trading_volume
        })
        
    except Exception as e:
        current_app.logger.error(f'获取仪表盘趋势数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'user_growth': {'labels': [], 'values': []},
            'trading_volume': {'labels': [], 'values': []}
        })

@admin_bp.route('/v2/api/dashboard/recent-trades', methods=['GET'])
def api_dashboard_recent_trades_v2():
    """获取最近交易数据"""
    try:
        limit = int(request.args.get('limit', 5))
        trades = Trade.query.order_by(Trade.created_at.desc()).limit(limit).all()
        
        return jsonify([{
            'id': trade.id,
            'asset': {
                'name': trade.asset.name if trade.asset else None,
                'token_symbol': trade.asset.token_symbol if trade.asset else None
            },
            'total_price': float(trade.total_price),
            'token_amount': trade.token_amount,
            'status': trade.status,
            'created_at': trade.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for trade in trades])
        
    except Exception as e:
        current_app.logger.error(f'获取最近交易数据失败: {str(e)}', exc_info=True)
        return jsonify([])

def get_user_growth_trend(days):
    """获取用户增长趋势数据"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 按日期分组统计新增用户数
    daily_stats = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date,
        User.created_at <= end_date
    ).group_by(
        func.date(User.created_at)
    ).all()
    
    # 生成日期标签和数据
    dates = [(start_date + timedelta(days=x)).strftime('%Y-%m-%d') for x in range(days)]
    counts = [0] * days
    
    # 填充实际数据
    date_dict = {stat.date.strftime('%Y-%m-%d'): stat.count for stat in daily_stats}
    for i, date in enumerate(dates):
        counts[i] = date_dict.get(date, 0)
    
    return {
        'labels': dates,
        'values': counts
    }

def get_trading_volume_trend(days):
    """获取交易量趋势数据"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 按日期分组统计交易量
    daily_stats = db.session.query(
        func.date(Trade.created_at).label('date'),
        func.sum(Trade.total_price).label('volume')
    ).filter(
        Trade.created_at >= start_date,
        Trade.created_at <= end_date
    ).group_by(
        func.date(Trade.created_at)
    ).all()
    
    # 生成日期标签和数据
    dates = [(start_date + timedelta(days=x)).strftime('%Y-%m-%d') for x in range(days)]
    volumes = [0] * days
    
    # 填充实际数据
    date_dict = {stat.date.strftime('%Y-%m-%d'): float(stat.volume) for stat in daily_stats}
    for i, date in enumerate(dates):
        volumes[i] = date_dict.get(date, 0)
    
    return {
        'labels': dates,
        'values': volumes
    }

@admin_api_bp.route('/update-dashboard-stats', methods=['POST'])
@admin_required
def update_dashboard_stats():
    """强制更新仪表盘统计数据"""
    try:
        # 尝试使用直接从数据库更新的方法
        if DashboardStats.update_stats_from_db():
            current_app.logger.info("仪表盘统计数据已成功更新")
            return jsonify({'success': True, 'message': '统计数据已成功更新'})
        else:
            current_app.logger.error("更新仪表盘统计数据失败")
            return jsonify({'success': False, 'message': '更新统计数据失败'}), 500
    except Exception as e:
        current_app.logger.error(f"更新仪表盘统计数据时发生错误: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'更新统计数据时发生错误: {str(e)}'}), 500

@admin_api_bp.route('/v2/share-messages', methods=['GET'])
@admin_required
def get_share_messages():
    """获取分享文案列表"""
    try:
        # 从数据库或配置文件中获取分享文案
        # 这里使用简单的JSON文件存储
        import os
        import json
        from flask import current_app
        
        # 确定文件路径
        file_path = os.path.join(current_app.root_path, 'static', 'data', 'share_messages.json')
        
        # 如果文件不存在，创建默认文案
        if not os.path.exists(file_path):
            default_messages = [
                "📈 分享赚佣金！邀请好友投资，您可获得高达30%的推广佣金！链接由您独享，佣金终身受益，朋友越多，收益越丰厚！",
                "🤝 好东西就要和朋友分享！发送您的专属链接，让更多朋友加入这个投资社区，一起交流，共同成长，还能获得持续佣金回报！",
                "🔥 发现好机会就要分享！邀请好友一起投资这个优质资产，共同见证财富增长！您的专属链接，助力朋友也能抓住这个机会！"
            ]
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存默认文案
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_messages, f, ensure_ascii=False, indent=2)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            messages = json.load(f)
            
        return jsonify({
            'success': True,
            'messages': messages
        }), 200
    except Exception as e:
        current_app.logger.error(f'获取分享文案失败: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api_bp.route('/v2/share-messages', methods=['POST'])
@admin_required
def update_share_messages():
    """更新分享文案"""
    try:
        import os
        import json
        from flask import current_app, request
        
        # 从请求中获取新的文案列表
        data = request.json
        if not data or 'messages' not in data or not isinstance(data['messages'], list):
            return jsonify({
                'success': False,
                'error': '无效的请求数据'
            }), 400
        
        messages = data['messages']
        
        # 验证文案列表
        if not all(isinstance(msg, str) for msg in messages):
            return jsonify({
                'success': False,
                'error': '所有文案必须是字符串'
            }), 400
        
        # 确定文件路径
        file_path = os.path.join(current_app.root_path, 'static', 'data', 'share_messages.json')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存新文案
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'success': True,
            'message': '分享文案已更新'
        }), 200
    except Exception as e:
        current_app.logger.error(f'更新分享文案失败: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/v2/api/users', methods=['GET'])
def api_users_v2():
    """管理后台V2版本用户列表API"""
    try:
        # 记录请求信息，方便调试
        current_app.logger.info(f"访问V2用户列表API，参数: {request.args}")
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # 查询用户列表
        query = User.query
        
        # 查询筛选条件
        keyword = request.args.get('keyword')
        role = request.args.get('role')
        
        if keyword:
            query = query.filter(
                or_(
                    User.eth_address.ilike(f'%{keyword}%'),
                    User.name.ilike(f'%{keyword}%'),
                    User.email.ilike(f'%{keyword}%')
                )
            )
            
        if role:
            query = query.filter(User.role == role)
        
        # 排序
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')
        
        if sort_order == 'desc':
            query = query.order_by(desc(getattr(User, sort_field)))
        else:
            query = query.order_by(getattr(User, sort_field))
        
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        users = pagination.items
        
        current_app.logger.info(f"查询到 {len(users)} 个用户，总计 {pagination.total} 个")
        
        # 格式化返回数据
        user_list = []
        for user in users:
            user_list.append({
                'id': user.id,
                'name': user.name,
                'eth_address': user.eth_address,
                'email': user.email,
                'role': user.role,
                'status': user.status,
                'verified': user.verified,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
            })
        
        return jsonify({
            'items': user_list,
            'total': pagination.total,
            'page': page,
            'limit': limit,
            'pages': pagination.pages
        })
    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'items': [],
            'total': 0,
            'page': 1,
            'limit': 10,
            'pages': 0
        })

@admin_bp.route('/v2/api/users/<int:user_id>', methods=['GET'])
def api_user_detail_v2(user_id):
    """管理后台V2版本用户详情API"""
    try:
        user = User.query.get_or_404(user_id)
        
        # 统计用户的资产数量
        asset_count = Asset.query.filter_by(owner_address=user.eth_address).count()
        
        # 获取用户的交易记录数量
        trade_count = Trade.query.filter_by(buyer_address=user.eth_address).count()
        
        return jsonify({
            'id': user.id,
            'name': user.name,
            'eth_address': user.eth_address,
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'status': user.status,
            'verified': user.verified,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            'asset_count': asset_count,
            'trade_count': trade_count
        })
    except Exception as e:
        current_app.logger.error(f"获取用户详情失败: {str(e)}", exc_info=True)
        return jsonify({
            'error': '获取用户详情失败',
            'message': str(e)
        }), 404

@admin_bp.route('/v2/api/users/<int:user_id>', methods=['PUT'])
def api_edit_user_v2(user_id):
    """管理后台V2版本编辑用户API"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # 更新用户信息
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data:
            user.role = data['role']
        if 'status' in data:
            user.status = data['status']
        if 'verified' in data:
            user.verified = data['verified']
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户更新成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新用户失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'更新用户失败: {str(e)}'
        }), 500

@admin_bp.route('/v2/api/users/<int:user_id>/verify', methods=['POST'])
def api_verify_user_v2(user_id):
    """管理后台V2版本验证用户API"""
    try:
        user = User.query.get_or_404(user_id)
        user.verified = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户验证成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"验证用户失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'验证用户失败: {str(e)}'
        }), 500

@admin_bp.route('/v2/api/users/<int:user_id>/reject', methods=['POST'])
def api_reject_user_v2(user_id):
    """管理后台V2版本拒绝用户API"""
    try:
        user = User.query.get_or_404(user_id)
        user.verified = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户拒绝成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"拒绝用户失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'拒绝用户失败: {str(e)}'
        }), 500

@admin_bp.route('/v2/api/users/batch-verify', methods=['POST'])
def api_batch_verify_users_v2():
    """管理后台V2版本批量验证用户API"""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({
                'success': False,
                'message': '未提供用户ID列表'
            }), 400
            
        users = User.query.filter(User.id.in_(user_ids)).all()
        
        for user in users:
            user.verified = True
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功验证{len(users)}个用户'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量验证用户失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'批量验证用户失败: {str(e)}'
        }), 500

@admin_bp.route('/v2/api/users/batch-reject', methods=['POST'])
def api_batch_reject_users_v2():
    """管理后台V2版本批量拒绝用户API"""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({
                'success': False,
                'message': '未提供用户ID列表'
            }), 400
            
        users = User.query.filter(User.id.in_(user_ids)).all()
        
        for user in users:
            user.verified = False
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功拒绝{len(users)}个用户'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量拒绝用户失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'批量拒绝用户失败: {str(e)}'
        }), 500

@admin_bp.route('/v2/api/users/export', methods=['GET'])
def api_export_users_v2():
    """管理后台V2版本导出用户API"""
    try:
        users = User.query.all()
        
        # 构建用户数据
        user_list = []
        for user in users:
            user_list.append({
                'id': user.id,
                'name': user.name,
                'eth_address': user.eth_address,
                'email': user.email,
                'role': user.role,
                'status': user.status,
                'verified': user.verified,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return jsonify(user_list)
    except Exception as e:
        current_app.logger.error(f"导出用户失败: {str(e)}", exc_info=True)
        return jsonify([]), 500

@admin_api_bp.route('/admin/v2/assets', methods=['GET'])
def api_admin_v2_assets():
    """管理后台V2版本资产列表API - 兼容路径"""
    try:
        # 记录请求信息，方便调试
        current_app.logger.info(f"访问兼容路径V2资产列表API，参数: {request.args}")
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # 查询资产列表 - 管理后台始终显示所有未删除的资产
        query = Asset.query.filter(Asset.status != 0)  # 0 表示已删除
        
        # 查询筛选条件
        status = request.args.get('status')
        asset_type = request.args.get('type')
        keyword = request.args.get('keyword')
        
        if status:
            query = query.filter(Asset.status == int(status))
        
        if asset_type:
            query = query.filter(Asset.asset_type == int(asset_type))
            
        if keyword:
            query = query.filter(
                or_(
                    Asset.name.ilike(f'%{keyword}%'),
                    Asset.description.ilike(f'%{keyword}%'),
                    Asset.token_symbol.ilike(f'%{keyword}%')
                )
            )
        
        # 排序
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')
        
        if sort_order == 'desc':
            query = query.order_by(desc(getattr(Asset, sort_field)))
        else:
            query = query.order_by(getattr(Asset, sort_field))
        
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        assets = pagination.items
        
        current_app.logger.info(f"查询到 {len(assets)} 个资产，总计 {pagination.total} 个")
        
        # 格式化返回数据
        asset_list = []
        for asset in assets:
            try:
                # 获取资产类型名称
                asset_type_name = '未知类型'
                asset_type_value = asset.asset_type
                
                # 尝试查找枚举值
                for item in AssetType:
                    if item.value == asset_type_value:
                        asset_type_name = item.name
                        break
                
                # 获取封面图片  
                cover_image = '/static/images/placeholder.jpg'
                if asset.images and len(asset.images) > 0:
                    cover_image = asset.images[0]
                        
                asset_list.append({
                    'id': asset.id,
                    'name': asset.name,
                    'token_symbol': asset.token_symbol,
                    'asset_type': asset.asset_type,
                    'asset_type_name': asset_type_name,
                    'location': asset.location,
                    'area': float(asset.area) if asset.area else 0,
                    'token_price': float(asset.token_price) if asset.token_price else 0,
                    'annual_revenue': float(asset.annual_revenue) if asset.annual_revenue else 0,
                    'total_value': float(asset.total_value) if asset.total_value else 0,
                    'token_supply': asset.token_supply,
                    'creator_address': asset.creator_address,
                    'status': asset.status,
                    'status_text': {
                        1: '待审核',
                        2: '已通过',
                        3: '已拒绝',
                        4: '已删除'
                    }.get(asset.status, '未知状态'),
                    'image': cover_image,
                    'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else None
                })
            except Exception as item_error:
                current_app.logger.error(f"处理资产 {asset.id} 数据失败: {str(item_error)}")
                # 继续处理下一个资产
        
        return jsonify({
            'items': asset_list,
            'total': pagination.total,
            'page': page,
            'limit': limit,
            'pages': pagination.pages
        })
    except Exception as e:
        current_app.logger.error(f"获取资产列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'items': [],
            'total': 0,
            'page': 1,
            'limit': 10,
            'pages': 0
        })

@admin_api_bp.route('/admin/v2/users', methods=['GET'])
def api_admin_v2_users():
    """管理后台V2版本用户列表API - 兼容路径"""
    try:
        # 记录请求信息，方便调试
        current_app.logger.info(f"访问兼容路径V2用户列表API，参数: {request.args}")
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # 查询用户列表
        query = User.query
        
        # 查询筛选条件
        keyword = request.args.get('keyword')
        role = request.args.get('role')
        
        if keyword:
            query = query.filter(
                or_(
                    User.eth_address.ilike(f'%{keyword}%'),
                    User.name.ilike(f'%{keyword}%'),
                    User.email.ilike(f'%{keyword}%')
                )
            )
            
        if role:
            query = query.filter(User.role == role)
        
        # 排序
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')
        
        if sort_order == 'desc':
            query = query.order_by(desc(getattr(User, sort_field)))
        else:
            query = query.order_by(getattr(User, sort_field))
        
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        users = pagination.items
        
        current_app.logger.info(f"查询到 {len(users)} 个用户，总计 {pagination.total} 个")
        
        # 格式化返回数据
        user_list = []
        for user in users:
            user_list.append({
                'id': user.id,
                'name': user.name,
                'eth_address': user.eth_address,
                'email': user.email,
                'role': user.role,
                'status': user.status,
                'verified': user.verified,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
            })
        
        return jsonify({
            'items': user_list,
            'total': pagination.total,
            'page': page,
            'limit': limit,
            'pages': pagination.pages
        })
    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'items': [],
            'total': 0,
            'page': 1,
            'limit': 10,
            'pages': 0
        })

@admin_api_bp.route('/admin/v2/dashboard/stats', methods=['GET'])
def api_admin_v2_dashboard_stats():
    """仪表盘统计数据API - 兼容路径"""
    try:
        # 获取用户统计
        total_users = User.query.count()
        new_users_today = User.query.filter(
            func.date(User.created_at) == func.date(datetime.now())
        ).count()
        
        # 获取资产统计
        total_assets = Asset.query.filter(Asset.status != 0).count()
        total_asset_value = db.session.query(func.sum(Asset.total_value)).filter(
            Asset.status == 2  # 只统计已审核通过的资产
        ).scalar() or 0
        
        # 获取交易统计
        total_trades = Trade.query.count()
        total_trade_volume = db.session.query(func.sum(Trade.total_price)).scalar() or 0
        
        return jsonify({
            'total_users': total_users,
            'new_users_today': new_users_today,
            'total_assets': total_assets,
            'total_asset_value': float(total_asset_value),
            'total_trades': total_trades,
            'total_trade_volume': float(total_trade_volume)
        })
        
    except Exception as e:
        current_app.logger.error(f'获取仪表盘统计数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'total_users': 0,
            'new_users_today': 0,
            'total_assets': 0,
            'total_asset_value': 0,
            'total_trades': 0,
            'total_trade_volume': 0
        })

# Helper function to validate Solana address (basic check)
def is_valid_solana_address(address):
    # Basic check for typical Solana address length and base58 characters
    import base58
    if not address or not (32 <= len(address) <= 44):
        return False
    try:
        base58.b58decode(address)
        return True
    except ValueError:
        return False