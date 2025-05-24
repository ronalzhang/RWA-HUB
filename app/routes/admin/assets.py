"""
资产管理模块
包含资产的增删改查、审核、导出等功能
"""

from flask import (
    render_template, request, jsonify, current_app, 
    send_file, make_response
)
from datetime import datetime
import csv
import io
from sqlalchemy import desc, func, or_, and_
from app import db
from app.models.asset import Asset, AssetType
from app.models.trade import Trade
from app.models.dividend import DividendRecord
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required


# 页面路由
@admin_bp.route('/assets')
@admin_page_required
def assets():
    """资产管理页面"""
    return render_template('admin/assets.html')


@admin_bp.route('/v2/assets')
@admin_page_required
def assets_v2():
    """V2版本资产管理页面"""
    return render_template('admin/assets.html')


# API路由
@admin_bp.route('/v2/api/assets', methods=['GET'])
@api_admin_required
def api_assets_v2():
    """V2版本资产列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status', '', type=str)
        asset_type = request.args.get('asset_type', '', type=str)
        
        # 查询资产列表 - 排除已删除的资产（状态4）
        query = Asset.query.filter(Asset.status != 4)
        
        # 搜索条件
        if search:
            query = query.filter(
                or_(
                    Asset.name.ilike(f'%{search}%'),
                    Asset.token_symbol.ilike(f'%{search}%'),
                    Asset.creator_address.ilike(f'%{search}%')
                )
            )
        
        # 状态筛选
        if status:
            query = query.filter(Asset.status == int(status))
        
        # 类型筛选
        if asset_type:
            query = query.filter(Asset.asset_type == int(asset_type))
        
        # 排序
        query = query.order_by(desc(Asset.created_at))
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        assets = []
        for asset in pagination.items:
            # 获取资产类型名称
            asset_type_name = '未知类型'
            try:
                for item in AssetType:
                    if item.value == asset.asset_type:
                        asset_type_name = item.name
                        break
            except:
                pass
            
            # 获取封面图片
            cover_image = '/static/images/placeholder.jpg'
            if asset.images and len(asset.images) > 0:
                cover_image = asset.images[0]
            
            assets.append({
                'id': asset.id,
                'name': asset.name,
                'token_symbol': asset.token_symbol,
                'asset_type': asset.asset_type,
                'asset_type_name': asset_type_name,
                'location': asset.location,
                'token_price': float(asset.token_price) if asset.token_price else 0,
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
                'token_address': asset.token_address,
                'image': cover_image,
                'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else None
            })
        
        return jsonify({
            'success': True,
            'data': assets,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/<int:asset_id>', methods=['GET'])
@api_admin_required
def api_get_asset_v2(asset_id):
    """获取单个资产详情"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 获取资产类型名称
        asset_type_name = '未知类型'
        try:
            for item in AssetType:
                if item.value == asset.asset_type:
                    asset_type_name = item.name
                    break
        except:
            pass
        
        cover_image = '/static/images/placeholder.jpg'
        if asset.images and len(asset.images) > 0:
            cover_image = asset.images[0]
        
        asset_data = {
            'id': asset.id,
            'name': asset.name,
            'description': asset.description,
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
            'token_address': asset.token_address,
            'image': cover_image,
            'images': asset.images if asset.images else [],
            'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else None
        }
        
        return jsonify({'success': True, 'data': asset_data})
        
    except Exception as e:
        current_app.logger.error(f'获取资产详情失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/<int:asset_id>', methods=['DELETE'])
@api_admin_required
def api_delete_asset_v2(asset_id):
    """删除资产（软删除）"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 软删除：将状态改为4（已删除）
        asset.status = 4
        db.session.commit()
        
        current_app.logger.info(f'资产已软删除: {asset_id}')
        return jsonify({'success': True, 'message': '资产已删除'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除资产失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/<int:asset_id>/approve', methods=['POST'])
@api_admin_required
def api_approve_asset_v2(asset_id):
    """审核通过资产"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        if asset.status != 1:
            return jsonify({'success': False, 'error': '只能审核待审核状态的资产'}), 400
        
        asset.status = 2  # 已通过
        db.session.commit()
        
        current_app.logger.info(f'资产审核通过: {asset_id}')
        return jsonify({'success': True, 'message': '资产审核通过'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'资产审核失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/<int:asset_id>/reject', methods=['POST'])
@api_admin_required
def api_reject_asset_v2(asset_id):
    """审核拒绝资产"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        if asset.status != 1:
            return jsonify({'success': False, 'error': '只能拒绝待审核状态的资产'}), 400
        
        data = request.get_json()
        reject_reason = data.get('reason', '管理员拒绝') if data else '管理员拒绝'
        
        asset.status = 3  # 已拒绝
        if hasattr(asset, 'reject_reason'):
            asset.reject_reason = reject_reason
        db.session.commit()
        
        current_app.logger.info(f'资产审核拒绝: {asset_id}')
        return jsonify({'success': True, 'message': '资产已拒绝'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'资产拒绝失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/batch-approve', methods=['POST'])
@api_admin_required
def api_batch_approve_assets_v2():
    """批量审核通过资产"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'success': False, 'error': '请提供要审核的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        success_count = 0
        failed_ids = []
        
        for asset_id in asset_ids:
            try:
                asset = Asset.query.get(asset_id)
                if asset and asset.status == 1:
                    asset.status = 2
                    success_count += 1
                else:
                    failed_ids.append(asset_id)
            except Exception as e:
                failed_ids.append(asset_id)
                
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功审核通过 {success_count} 个资产',
            'success_count': success_count,
            'failed_ids': failed_ids
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量审核失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/batch-reject', methods=['POST'])
@api_admin_required
def api_batch_reject_assets_v2():
    """批量审核拒绝资产"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'success': False, 'error': '请提供要拒绝的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        reject_reason = data.get('reason', '管理员批量拒绝')
        success_count = 0
        failed_ids = []
        
        for asset_id in asset_ids:
            try:
                asset = Asset.query.get(asset_id)
                if asset and asset.status == 1:
                    asset.status = 3
                    if hasattr(asset, 'reject_reason'):
                        asset.reject_reason = reject_reason
                    success_count += 1
                else:
                    failed_ids.append(asset_id)
            except Exception as e:
                failed_ids.append(asset_id)
                
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功拒绝 {success_count} 个资产',
            'success_count': success_count,
            'failed_ids': failed_ids
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量拒绝失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/batch-delete', methods=['POST'])
@api_admin_required
def api_batch_delete_assets_v2():
    """批量删除资产（软删除）"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'success': False, 'error': '请提供要删除的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        success_count = 0
        failed_ids = []
        
        for asset_id in asset_ids:
            try:
                asset = Asset.query.get(asset_id)
                if asset:
                    asset.status = 4  # 软删除
                    success_count += 1
                else:
                    failed_ids.append(asset_id)
            except Exception as e:
                failed_ids.append(asset_id)
                
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功删除 {success_count} 个资产',
            'success_count': success_count,
            'failed_ids': failed_ids
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量删除失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/stats', methods=['GET'])
@api_admin_required
def api_assets_stats_v2():
    """资产统计数据"""
    try:
        total_assets = Asset.query.filter(Asset.status != 4).count()
        pending_assets = Asset.query.filter(Asset.status == 1).count()
        approved_assets = Asset.query.filter(Asset.status == 2).count()
        rejected_assets = Asset.query.filter(Asset.status == 3).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total_assets,
                'pending': pending_assets,
                'approved': approved_assets,
                'rejected': rejected_assets
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产统计失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/v2/api/assets/export', methods=['GET'])
@api_admin_required
def api_export_assets_v2():
    """导出资产数据为CSV"""
    try:
        assets = Asset.query.filter(Asset.status != 4).order_by(desc(Asset.created_at)).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        writer.writerow([
            'ID', '资产名称', 'Token符号', '资产类型', '位置', 
            'Token价格', '总价值', '发行量', '创建者地址', '状态', 
            '创建时间', '更新时间'
        ])
        
        # 写入数据行
        for asset in assets:
            status_text = {
                1: '待审核',
                2: '已通过',
                3: '已拒绝'
            }.get(asset.status, '未知状态')
            
            writer.writerow([
                asset.id,
                asset.name,
                asset.token_symbol,
                asset.asset_type,
                asset.location,
                float(asset.token_price) if asset.token_price else 0,
                float(asset.total_value) if asset.total_value else 0,
                asset.token_supply,
                asset.creator_address,
                status_text,
                asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else ''
            ])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=assets_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f'导出资产数据失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500 