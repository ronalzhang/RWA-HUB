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
from sqlalchemy import desc, func, or_, and_, text
from app import db
from app.models.asset import Asset, AssetType
from app.models.trade import Trade
from app.models.dividend import DividendRecord
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required


# 页面路由
@admin_bp.route('/assets')
@admin_page_required
def assets_page():
    """资产管理页面"""
    return render_template('admin_v2/assets.html')


# V2版本路由（兼容前端调用）
@admin_bp.route('/v2/api/assets', methods=['GET'])
@api_admin_required
def assets_list_v2():
    """获取资产列表 - V2兼容版本"""
    return api_assets()


@admin_bp.route('/v2/api/assets/<int:asset_id>', methods=['GET'])
@api_admin_required
def asset_detail_v2(asset_id):
    """获取资产详情 - V2兼容版本"""
    return api_get_asset(asset_id)


@admin_bp.route('/v2/api/assets/<int:asset_id>', methods=['DELETE'])
@api_admin_required
def delete_asset_v2(asset_id):
    """删除资产 - V2兼容版本"""
    return api_delete_asset(asset_id)


@admin_bp.route('/v2/api/assets/<int:asset_id>/approve', methods=['POST'])
@api_admin_required
def approve_asset_v2(asset_id):
    """审核通过资产 - V2兼容版本"""
    return api_approve_asset(asset_id)


@admin_bp.route('/v2/api/assets/<int:asset_id>/reject', methods=['POST'])
@api_admin_required
def reject_asset_v2(asset_id):
    """审核拒绝资产 - V2兼容版本"""
    return api_reject_asset(asset_id)


@admin_bp.route('/v2/api/assets/batch-approve', methods=['POST'])
@api_admin_required
def batch_approve_assets_v2():
    """批量审核通过 - V2兼容版本"""
    return api_batch_approve_assets()


@admin_bp.route('/v2/api/assets/batch-reject', methods=['POST'])
@api_admin_required
def batch_reject_assets_v2():
    """批量审核拒绝 - V2兼容版本"""
    return api_batch_reject_assets()


@admin_bp.route('/v2/api/assets/batch-delete', methods=['POST'])
@api_admin_required
def batch_delete_assets_v2():
    """批量删除 - V2兼容版本"""
    return api_batch_delete_assets()


@admin_bp.route('/v2/api/assets/stats', methods=['GET'])
@api_admin_required
def assets_stats_v2():
    """获取资产统计 - V2兼容版本"""
    return api_assets_stats()


@admin_bp.route('/v2/api/assets/export', methods=['GET'])
@api_admin_required
def export_assets_v2():
    """导出资产数据 - V2兼容版本"""
    return api_export_assets()


# API路由
@admin_bp.route('/api/assets', methods=['GET'])
@api_admin_required
def api_assets():
    """资产列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        # 兼容前端的limit参数
        limit = request.args.get('limit', 20, type=int)
        per_page = request.args.get('per_page', limit, type=int)
        
        # 兼容前端的keyword参数
        search = request.args.get('search', '')
        keyword = request.args.get('keyword', '')
        if keyword:
            search = keyword
            
        status = request.args.get('status', '', type=str)
        # 兼容前端的type参数
        asset_type = request.args.get('asset_type', '', type=str)
        type_param = request.args.get('type', '')
        if type_param:
            asset_type = type_param
            
        # 获取排序参数
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')
        
        # 查询资产列表 - 排除已删除的资产（deleted_at不为空）
        query = Asset.query.filter(Asset.deleted_at.is_(None))
        
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
            try:
                query = query.filter(Asset.status == int(status))
            except ValueError:
                pass
        
        # 类型筛选
        if asset_type:
            try:
                query = query.filter(Asset.asset_type == int(asset_type))
            except ValueError:
                pass
        
        # 排序处理
        if sort_field == 'id':
            order_column = Asset.id
        elif sort_field == 'name':
            order_column = Asset.name
        elif sort_field == 'created_at':
            order_column = Asset.created_at
        elif sort_field == 'updated_at':
            order_column = Asset.updated_at
        elif sort_field == 'token_price':
            order_column = Asset.token_price
        elif sort_field == 'total_value':
            order_column = Asset.total_value
        else:
            order_column = Asset.id
            
        if sort_order.lower() == 'asc':
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        assets = []
        for asset in pagination.items:
            # 获取资产类型名称
            asset_type_name = '其他'
            try:
                if asset.asset_type == 1:
                    asset_type_name = '房地产'
                elif asset.asset_type == 2:
                    asset_type_name = '股权'
                elif asset.asset_type == 3:
                    asset_type_name = '债券'
                elif asset.asset_type == 4:
                    asset_type_name = '商品'
                elif asset.asset_type == 5:
                    asset_type_name = '其他'
                elif asset.asset_type == 10:
                    asset_type_name = '不动产'
                elif asset.asset_type == 20:
                    asset_type_name = '商业地产'
                elif asset.asset_type == 30:
                    asset_type_name = '工业地产'
                elif asset.asset_type == 40:
                    asset_type_name = '土地资产'
                elif asset.asset_type == 50:
                    asset_type_name = '证券资产'
                elif asset.asset_type == 60:
                    asset_type_name = '艺术品'
                elif asset.asset_type == 70:
                    asset_type_name = '收藏品'
                else:
                    asset_type_name = '其他'
            except:
                asset_type_name = '其他'
            
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
            'items': assets,
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages,
            'per_page': per_page,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/assets/<int:asset_id>', methods=['GET'])
@api_admin_required
def api_get_asset(asset_id):
    """获取单个资产详情"""
    try:
        asset = Asset.query.filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在或已被删除'}), 404
        
        # 获取资产类型名称
        asset_type_name = '其他'
        try:
            if asset.asset_type == 1:
                asset_type_name = '房地产'
            elif asset.asset_type == 2:
                asset_type_name = '股权'
            elif asset.asset_type == 3:
                asset_type_name = '债券'
            elif asset.asset_type == 4:
                asset_type_name = '商品'
            elif asset.asset_type == 5:
                asset_type_name = '其他'
            elif asset.asset_type == 10:
                asset_type_name = '不动产'
            elif asset.asset_type == 20:
                asset_type_name = '商业地产'
            elif asset.asset_type == 30:
                asset_type_name = '工业地产'
            elif asset.asset_type == 40:
                asset_type_name = '土地资产'
            elif asset.asset_type == 50:
                asset_type_name = '证券资产'
            elif asset.asset_type == 60:
                asset_type_name = '艺术品'
            elif asset.asset_type == 70:
                asset_type_name = '收藏品'
            else:
                asset_type_name = '其他'
        except:
            asset_type_name = '其他'
        
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


@admin_bp.route('/api/assets/<int:asset_id>', methods=['DELETE'])
@api_admin_required
def api_delete_asset(asset_id):
    """删除资产（软删除）"""
    try:
        with current_app.app_context():
            # 首先检查资产是否存在
            asset = Asset.query.filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
            if not asset:
                return jsonify({'success': False, 'error': '资产不存在或已被删除'}), 404
            
            # 使用原生SQL执行软删除
            sql = text("UPDATE assets SET deleted_at = NOW() WHERE id = :asset_id AND deleted_at IS NULL")
            result = db.session.execute(sql, {'asset_id': asset_id})
            
            if result.rowcount > 0:
                db.session.commit()
                current_app.logger.info(f'资产已软删除: {asset_id}')
                return jsonify({'success': True, 'message': '资产已删除'})
            else:
                return jsonify({'success': False, 'error': '删除失败，资产可能已被删除'}), 400
        
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        current_app.logger.error(f'删除资产失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/assets/<int:asset_id>/approve', methods=['POST'])
@api_admin_required
def api_approve_asset(asset_id):
    """审核通过资产"""
    try:
        asset = Asset.query.filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在或已被删除'}), 404
        
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


@admin_bp.route('/api/assets/<int:asset_id>/reject', methods=['POST'])
@api_admin_required
def api_reject_asset(asset_id):
    """审核拒绝资产"""
    try:
        asset = Asset.query.filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在或已被删除'}), 404
        
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


@admin_bp.route('/api/assets/batch-approve', methods=['POST'])
@api_admin_required
def api_batch_approve_assets():
    """批量审核通过资产"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'success': False, 'error': '请提供要审核的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        if not asset_ids:
            return jsonify({'success': False, 'error': '资产ID列表不能为空'}), 400
        
        # 验证所有asset_ids都是整数
        try:
            asset_ids = [int(aid) for aid in asset_ids]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': '无效的资产ID格式'}), 400
        
        # 使用原生SQL执行批量审核通过
        from sqlalchemy import text
        sql = text("UPDATE assets SET status = 2 WHERE id = ANY(:asset_ids) AND status = 1 AND deleted_at IS NULL")
        result = db.session.execute(sql, {'asset_ids': asset_ids})
        
        success_count = result.rowcount
        failed_count = len(asset_ids) - success_count
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功审核通过 {success_count} 个资产',
            'success_count': success_count,
            'failed_count': failed_count,
            'total_requested': len(asset_ids)
        })
        
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        current_app.logger.error(f'批量审核失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/assets/batch-reject', methods=['POST'])
@api_admin_required
def api_batch_reject_assets():
    """批量审核拒绝资产"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'success': False, 'error': '请提供要拒绝的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        reject_reason = data.get('reason', '管理员批量拒绝')
        
        if not asset_ids:
            return jsonify({'success': False, 'error': '资产ID列表不能为空'}), 400
        
        # 验证所有asset_ids都是整数
        try:
            asset_ids = [int(aid) for aid in asset_ids]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': '无效的资产ID格式'}), 400
        
        # 使用原生SQL执行批量审核拒绝
        from sqlalchemy import text
        sql = text("UPDATE assets SET status = 3 WHERE id = ANY(:asset_ids) AND status = 1 AND deleted_at IS NULL")
        result = db.session.execute(sql, {'asset_ids': asset_ids})
        
        success_count = result.rowcount
        failed_count = len(asset_ids) - success_count
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功拒绝 {success_count} 个资产',
            'success_count': success_count,
            'failed_count': failed_count,
            'total_requested': len(asset_ids)
        })
        
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        current_app.logger.error(f'批量拒绝失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/assets/batch-delete', methods=['POST'])
@api_admin_required
def api_batch_delete_assets():
    """批量删除资产（软删除）"""
    try:
        data = request.get_json()
        if not data or 'asset_ids' not in data:
            return jsonify({'success': False, 'error': '请提供要删除的资产ID列表'}), 400
            
        asset_ids = data['asset_ids']
        if not asset_ids:
            return jsonify({'success': False, 'error': '资产ID列表不能为空'}), 400
        
        # 验证所有asset_ids都是整数
        try:
            asset_ids = [int(aid) for aid in asset_ids]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': '无效的资产ID格式'}), 400
        
        # 使用原生SQL执行批量软删除
        from sqlalchemy import text
        
        # 先检查有多少资产存在且未被删除
        check_sql = text("SELECT COUNT(*) FROM assets WHERE id = ANY(:asset_ids) AND deleted_at IS NULL")
        exist_count = db.session.execute(check_sql, {'asset_ids': asset_ids}).scalar()
        
        # 执行批量软删除
        sql = text("UPDATE assets SET deleted_at = NOW() WHERE id = ANY(:asset_ids) AND deleted_at IS NULL")
        result = db.session.execute(sql, {'asset_ids': asset_ids})
        
        success_count = result.rowcount
        failed_count = len(asset_ids) - success_count
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功删除 {success_count} 个资产',
            'success_count': success_count,
            'failed_count': failed_count,
            'total_requested': len(asset_ids)
        })
        
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        current_app.logger.error(f'批量删除失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/assets/stats', methods=['GET'])
@api_admin_required
def api_assets_stats():
    """资产统计数据"""
    try:
        total_assets = Asset.query.filter(Asset.deleted_at.is_(None)).count()
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


@admin_bp.route('/api/assets/export', methods=['GET'])
@api_admin_required
def api_export_assets():
    """导出资产数据为CSV"""
    try:
        assets = Asset.query.filter(Asset.deleted_at.is_(None)).order_by(desc(Asset.created_at)).all()
        
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