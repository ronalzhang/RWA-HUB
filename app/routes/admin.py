from flask import render_template, jsonify, request, g, current_app, redirect, url_for, flash, session
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade
from app import db
from . import admin_bp, admin_api_bp
from app.utils.decorators import eth_address_required
from sqlalchemy import func
from datetime import datetime, timedelta
from functools import wraps
import json
import os
from app.utils.storage import storage
from ..models import DividendRecord

def get_admin_permissions(eth_address):
    """获取管理员权限"""
    if not eth_address:
        return None
        
    # 转换为小写进行比较
    eth_address = eth_address.lower()
    admin_config = current_app.config['ADMIN_CONFIG']
    admin_info = None
    
    # 检查地址是否在管理员配置中
    for admin_address, info in admin_config.items():
        if eth_address == admin_address.lower():
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
    return get_admin_permissions(target_address) is not None

def has_permission(permission, eth_address=None):
    """检查管理员是否有特定权限"""
    target_address = eth_address if eth_address else g.eth_address if hasattr(g, 'eth_address') else None
    admin_info = get_admin_permissions(target_address)
    
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
    admin_info = get_admin_permissions(target_address)
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
        if not is_admin():
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    admin_check.__name__ = f.__name__
    return admin_check

def permission_required(permission):
    """特定权限装饰器"""
    def decorator(f):
        @eth_address_required
        def permission_check(*args, **kwargs):
            if not has_permission(permission):
                return jsonify({'error': f'需要{permission}权限'}), 403
            return f(*args, **kwargs)
        permission_check.__name__ = f.__name__
        return permission_check
    return decorator

def admin_page_required(f):
    """管理员页面权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 优先从URL参数获取钱包地址
        eth_address = request.args.get('eth_address') or \
                     request.headers.get('X-Eth-Address') or \
                     request.cookies.get('eth_address')
                     
        current_app.logger.info(f'管理后台访问 - 钱包地址: {eth_address}')
        
        if not eth_address:
            current_app.logger.warning('管理后台访问被拒绝 - 未提供钱包地址')
            return redirect(url_for('main.index'))
            
        admin_info = get_admin_permissions(eth_address)
        current_app.logger.info(f'管理员信息: {admin_info}')
        
        if not admin_info:
            current_app.logger.warning(f'管理后台访问被拒绝 - 非管理员地址: {eth_address}')
            return redirect(url_for('main.index'))
            
        g.eth_address = eth_address
        g.admin_info = admin_info  # 保存管理员信息到g对象
        current_app.logger.info(f'管理后台访问成功 - 管理员: {eth_address}')
        return f(*args, **kwargs)
    return decorated_function

# 页面路由
@admin_bp.route('/')
@admin_page_required
def index():
    """后台管理首页"""
    try:
        eth_address = request.args.get('eth_address') or \
                     request.headers.get('X-Eth-Address') or \
                     request.cookies.get('eth_address')
                     
        if not eth_address:
            current_app.logger.warning('访问后台管理页面失败：未提供钱包地址')
            flash('请先连接钱包', 'error')
            return redirect(url_for('main.index'))
            
        admin_info = get_admin_permissions(eth_address)
        if not admin_info:
            current_app.logger.warning(f'访问后台管理页面失败：非管理员地址 {eth_address}')
            flash('您没有管理员权限', 'error')
            return redirect(url_for('main.index'))
            
        # 将管理员信息保存到session中
        session['admin_eth_address'] = eth_address
        session['admin_info'] = admin_info
            
        return render_template('admin/dashboard.html', admin_info=admin_info)
    except Exception as e:
        current_app.logger.error(f'访问后台管理页面失败：{str(e)}')
        flash('系统错误，请稍后重试', 'error')
        return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
@admin_page_required
def dashboard():
    """后台管理仪表板"""
    return render_template('admin/dashboard.html')

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

# API路由
@admin_api_bp.route('/stats')
@admin_required
def get_admin_stats():
    """获取管理统计数据"""
    try:
        current_app.logger.info('开始获取管理统计数据...')
        
        # 获取用户数量（根据唯一的owner_address计数）
        total_users = db.session.query(db.func.count(db.func.distinct(Asset.owner_address))).scalar() or 0
        
        # 获取各状态资产数量和总价值
        asset_stats = db.session.query(
            Asset.status,
            db.func.count(Asset.id).label('count'),
            db.func.coalesce(db.func.sum(Asset.total_value), 0).label('total_value')
        ).group_by(Asset.status).all()
        
        # 初始化状态计数和价值
        status_counts = {
            AssetStatus.PENDING.value: 0,
            AssetStatus.APPROVED.value: 0,
            AssetStatus.REJECTED.value: 0
        }
        approved_value = 0  # 已通过资产的总价值
        
        # 更新实际计数和价值
        for status, count, value in asset_stats:
            if status in status_counts:
                status_counts[status] = count
                if status == AssetStatus.APPROVED.value:
                    approved_value = float(value)
        
        # 获取实际交易总金额
        total_trades = db.session.query(
            db.func.coalesce(db.func.sum(Trade.amount), 0)
        ).scalar() or 0
        
        response_data = {
            'total_users': total_users,
            'pending_assets': status_counts[AssetStatus.PENDING.value],
            'approved_assets': status_counts[AssetStatus.APPROVED.value],
            'rejected_assets': status_counts[AssetStatus.REJECTED.value],
            'total_value': float(total_trades),  # 使用实际交易总额
            'approved_assets_value': approved_value  # 已通过资产的总价值
        }
        
        current_app.logger.info(f'返回数据: {response_data}')
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f'获取统计数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': '获取统计数据失败',
            'message': str(e)
        }), 500

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
    """获取所有资产列表"""
    try:
        current_app.logger.info('开始获取资产列表...')
        current_app.logger.info(f'请求头: {dict(request.headers)}')
        
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        search = request.args.get('search', '')
        
        current_app.logger.info(f'查询参数: page={page}, page_size={page_size}, search={search}')

        # 构建查询
        query = Asset.query
        current_app.logger.info('初始查询构建完成')

        # 过滤掉已删除的资产 - 使用明确的条件
        current_app.logger.info(f'删除状态值: {AssetStatus.DELETED.value}')
        query = query.filter(
            Asset.status.in_([
                AssetStatus.PENDING.value,
                AssetStatus.APPROVED.value,
                AssetStatus.REJECTED.value
            ])
        )
        current_app.logger.info('添加状态过滤条件')

        # 验证过滤是否生效
        test_query = query.all()
        current_app.logger.info('过滤后的资产状态:')
        for asset in test_query:
            current_app.logger.info(f'资产ID: {asset.id}, 状态: {asset.status}')

        # 搜索条件
        if search:
            query = query.filter(
                db.or_(
                    Asset.name.ilike(f'%{search}%'),
                    Asset.location.ilike(f'%{search}%'),
                    Asset.token_symbol.ilike(f'%{search}%')
                )
            )

        # 获取总数
        total = query.count()
        current_app.logger.info(f'符合条件的资产总数: {total}')

        # 分页并按创建时间倒序排序
        pagination = query.order_by(Asset.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        # 转换为字典格式
        assets = []
        for asset in pagination.items:
            try:
                asset_dict = asset.to_dict()
                # 添加额外的状态文本
                status_text = {
                    1: '待审核',
                    2: '已通过',
                    3: '已拒绝',
                    4: '已删除'
                }.get(asset.status, '未知状态')
                asset_dict['status_text'] = status_text
                assets.append(asset_dict)
            except Exception as e:
                current_app.logger.error(f'转换资产数据失败 (ID: {asset.id}): {str(e)}')
                continue

        current_app.logger.info(f'成功获取 {len(assets)} 个资产数据')
        
        response_data = {
            'total': total,
            'current_page': page,
            'page_size': page_size,
            'total_pages': pagination.pages,
            'assets': assets
        }
        
        current_app.logger.info(f'返回数据: {response_data}')
        return jsonify(response_data)

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
            return jsonify({'error': '请提供要删除的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        current_app.logger.info(f'批量删除资产请求: asset_ids={asset_ids}')
        
        success_count = 0
        failed_ids = []
        
        for asset_id in asset_ids:
            try:
                asset = Asset.query.get(asset_id)
                if not asset:
                    failed_ids.append(asset_id)
                    continue
                    
                if asset.token_address:
                    failed_ids.append(asset_id)
                    continue
                    
                # 删除关联记录
                DividendRecord.query.filter_by(asset_id=asset_id).delete()
                Trade.query.filter_by(asset_id=asset_id).delete()
                
                # 删除资产
                db.session.delete(asset)
                success_count += 1
                
            except Exception as e:
                current_app.logger.error(f'删除资产 {asset_id} 失败: {str(e)}')
                failed_ids.append(asset_id)
                continue
                
        db.session.commit()
        
        return jsonify({
            'message': f'成功删除 {success_count} 个资产',
            'failed_ids': failed_ids
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量删除资产失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

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
@admin_api_bp.route('/check')
def check_admin():
    """检查管理员权限"""
    try:
        eth_address = request.headers.get('X-Eth-Address') or \
                     request.args.get('eth_address') or \
                     session.get('admin_eth_address')
                     
        current_app.logger.info(f'检查管理员权限 - 地址: {eth_address}')
        
        if not eth_address:
            current_app.logger.warning('未提供钱包地址')
            return jsonify({'is_admin': False}), 200
            
        # 转换为小写进行比较
        eth_address = eth_address.lower()
        current_app.logger.info(f'检查管理员权限 - 地址(小写): {eth_address}')
        
        admin_data = get_admin_permissions(eth_address)
        is_admin = bool(admin_data)
        
        if not is_admin:
            current_app.logger.warning('未找到管理员权限')
            session.pop('admin_eth_address', None)
            session.pop('admin_info', None)
        else:
            session['admin_eth_address'] = eth_address
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
            asset.approved_at = datetime.utcnow()
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
            asset.approved_at = datetime.utcnow()
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