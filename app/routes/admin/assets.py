"""
资产管理模块
包含资产的增删改查、审核、导出等功能
"""

from flask import (
    render_template, request, jsonify, current_app, 
    send_file, make_response, Response
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


# 资产类型映射
ASSET_TYPE_NAMES = {
    1: '房地产',
    2: '股权', 
    3: '债券',
    4: '商品',
    5: '其他',
    10: '不动产',
    20: '商业地产',
    30: '工业地产',
    40: '土地资产',
    50: '证券资产',
    60: '艺术品',
    70: '收藏品'
}

# 状态文本映射
STATUS_TEXTS = {
    1: '待审核',
    2: '已通过',
    3: '已拒绝',
    5: '已支付',
    6: '支付失败',
    7: '部署失败',
    8: '支付处理中'
}


def get_asset_type_name(asset_type):
    """获取资产类型名称"""
    return ASSET_TYPE_NAMES.get(asset_type, '其他')


def get_status_text(status):
    """获取状态文本"""
    return STATUS_TEXTS.get(status, '未知状态')


def format_asset_data(asset):
    """格式化单个资产数据"""
    # 获取封面图片
    cover_image = '/static/images/placeholder.jpg'
    if asset.images and len(asset.images) > 0:
        cover_image = asset.images[0]
    
    return {
        'id': asset.id,
        'name': asset.name,
        'token_symbol': asset.token_symbol,
        'asset_type': asset.asset_type,
        'asset_type_name': get_asset_type_name(asset.asset_type),
        'location': asset.location,
        'area': float(asset.area) if asset.area else 0,
        'token_price': float(asset.token_price) if asset.token_price else 0,
        'annual_revenue': float(asset.annual_revenue) if asset.annual_revenue else 0,
        'total_value': float(asset.total_value) if asset.total_value else 0,
        'token_supply': asset.token_supply,
        'creator_address': asset.creator_address,
        'status': asset.status,
        'status_text': get_status_text(asset.status),
        'token_address': asset.token_address,
        'image': cover_image,
        'images': asset.images if asset.images else [],
        'description': asset.description,
        'created_at': asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': asset.updated_at.strftime('%Y-%m-%d %H:%M:%S') if asset.updated_at else None
    }


# ================================
# 页面路由
# ================================

@admin_bp.route('/assets')
@admin_page_required  
def assets_page():
    """资产管理页面"""
    return render_template('admin_v2/assets.html')


# ================================
# API路由 - 资产管理
# ================================

@admin_api_bp.route('/assets', methods=['GET'])
@api_admin_required
def api_assets():
    """资产列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        # 搜索参数
        search = request.args.get('search', '')
        keyword = request.args.get('keyword', '')
        if keyword:
            search = keyword
            
        # 筛选参数
        status = request.args.get('status', '', type=str)
        asset_type = request.args.get('asset_type', '', type=str) or request.args.get('type', '')
        
        # 排序参数
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')
        
        # 构建查询
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
        sort_columns = {
            'id': Asset.id,
            'name': Asset.name,
            'created_at': Asset.created_at,
            'updated_at': Asset.updated_at,
            'token_price': Asset.token_price,
            'total_value': Asset.total_value
        }
        
        order_column = sort_columns.get(sort_field, Asset.id)
        if sort_order.lower() == 'asc':
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())
        
        # 分页
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        
        # 格式化数据
        assets = [format_asset_data(asset) for asset in pagination.items]
        
        return jsonify({
            'success': True,
            'items': assets,
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages,
            'per_page': limit,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产列表失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/assets/<int:asset_id>', methods=['GET'])
@api_admin_required
def api_get_asset(asset_id):
    """获取单个资产详情"""
    try:
        asset = Asset.query.filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
        if not asset:
            return jsonify({'success': False, 'error': '资产不存在或已被删除'}), 404
        
        return jsonify({'success': True, 'data': format_asset_data(asset)})
        
    except Exception as e:
        current_app.logger.error(f'获取资产详情失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/assets/<int:asset_id>', methods=['DELETE'])
@api_admin_required
def api_delete_asset(asset_id):
    """删除资产（软删除）"""
    try:
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
        db.session.rollback()
        current_app.logger.error(f'删除资产失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/assets/<int:asset_id>/approve', methods=['POST'])
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


@admin_api_bp.route('/assets/<int:asset_id>/reject', methods=['POST'])
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


@admin_api_bp.route('/assets/batch-approve', methods=['POST'])
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
        
        # 批量审核通过
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
        db.session.rollback()
        current_app.logger.error(f'批量审核失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/assets/batch-reject', methods=['POST'])
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
        
        # 批量审核拒绝
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
        db.session.rollback()
        current_app.logger.error(f'批量拒绝失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/assets/batch-delete', methods=['POST'])
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
        
        # 批量软删除
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
        db.session.rollback()
        current_app.logger.error(f'批量删除失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/assets/stats', methods=['GET'])
@api_admin_required
def api_assets_stats():
    """资产统计数据"""
    try:
        total_assets = Asset.query.filter(Asset.deleted_at.is_(None)).count()
        pending_assets = Asset.query.filter(Asset.status == 1, Asset.deleted_at.is_(None)).count()
        approved_assets = Asset.query.filter(Asset.status == 2, Asset.deleted_at.is_(None)).count()
        rejected_assets = Asset.query.filter(Asset.status == 3, Asset.deleted_at.is_(None)).count()
        
        # 计算总价值 (只统计已审核通过且未删除的资产)
        total_value = db.session.query(func.sum(Asset.total_value)).filter(
            Asset.status == 2, 
            Asset.deleted_at.is_(None)
        ).scalar() or 0
        
        # 计算资产类型数量
        asset_types_count = db.session.query(Asset.asset_type).filter(
            Asset.deleted_at.is_(None)
        ).distinct().count()
        
        return jsonify({
            'totalAssets': total_assets,
            'totalValue': float(total_value),
            'pendingAssets': pending_assets,
            'assetTypes': asset_types_count,
            'approvedAssets': approved_assets,
            'rejectedAssets': rejected_assets
        })
        
    except Exception as e:
        current_app.logger.error(f'获取资产统计失败: {str(e)}')
        return jsonify({
            'totalAssets': 0,
            'totalValue': 0,
            'pendingAssets': 0,
            'assetTypes': 0,
            'approvedAssets': 0,
            'rejectedAssets': 0
        }), 500


@admin_api_bp.route('/assets/export', methods=['GET'])
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
            writer.writerow([
                asset.id,
                asset.name,
                asset.token_symbol,
                get_asset_type_name(asset.asset_type),
                asset.location,
                float(asset.token_price) if asset.token_price else 0,
                float(asset.total_value) if asset.total_value else 0,
                asset.token_supply,
                asset.creator_address,
                get_status_text(asset.status),
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


# ================================
# API路由 - 分红管理  
# ================================

@admin_api_bp.route('/dividends', methods=['GET'])
@api_admin_required
def api_get_dividends():
    """获取分红列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 10, type=int), 100)
        asset_id = request.args.get('asset_id')
        status = request.args.get('status')
        sort = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        
        # 由于目前没有实际的分红表，返回空结果
        return jsonify({
            'success': True,
            'dividends': [],
            'page': page,
            'limit': limit,
            'total': 0,
            'pages': 0
        })
        
    except Exception as e:
        current_app.logger.error(f'获取分红列表失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/dividends/<int:dividend_id>/process', methods=['POST'])
@api_admin_required
def api_process_dividend(dividend_id):
    """处理分红"""
    try:
        return jsonify({'success': True, 'message': '分红处理功能暂未实现'})
    except Exception as e:
        current_app.logger.error(f'处理分红失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/dividends/<int:dividend_id>', methods=['DELETE'])
@api_admin_required
def api_delete_dividend(dividend_id):
    """删除分红"""
    try:
        return jsonify({'success': True, 'message': '分红删除功能暂未实现'})
    except Exception as e:
        current_app.logger.error(f'删除分红失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/dividends/export', methods=['GET'])
@api_admin_required
def api_export_dividends():
    """导出分红数据"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '资产名称', '分红金额', '状态', '创建时间'])
        
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=dividends.csv'}
        )
        return response
        
    except Exception as e:
        current_app.logger.error(f'导出分红数据失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500 

@admin_api_bp.route('/assets/fix-all-contracts', methods=['POST'])
@api_admin_required
def api_fix_all_contracts():
    """批量修复所有资产的合约地址"""
    try:
        # 查询需要修复的资产（状态为2且没有token_address的资产）
        assets_to_fix = Asset.query.filter(
            Asset.status == 2,  # 只处理已通过的资产
            or_(Asset.token_address.is_(None), Asset.token_address == '')
        ).all()
        
        if not assets_to_fix:
            return jsonify({
                'success': True,
                'message': '没有需要修复的资产',
                'fixed_count': 0,
                'total_count': 0
            })
        
        from app.blockchain.rwa_contract_service import rwa_contract_service
        import json
        
        fixed_count = 0
        failed_assets = []
        
        for asset in assets_to_fix:
            try:
                # 生成合约地址
                contract_result = rwa_contract_service.create_asset_directly(
                    creator_address=asset.creator_address,
                    asset_name=asset.name,
                    asset_symbol=asset.token_symbol,
                    total_supply=asset.token_supply,
                    decimals=0,
                    price_per_token=asset.token_price
                )
                
                if contract_result['success']:
                    # 更新资产信息
                    asset.token_address = contract_result['mint_account']
                    asset.blockchain_data = json.dumps(contract_result['blockchain_data'])
                    asset.updated_at = datetime.now()
                    
                    fixed_count += 1
                    current_app.logger.info(f"资产 {asset.id} 合约地址修复成功: {asset.token_address}")
                else:
                    failed_assets.append({
                        'id': asset.id,
                        'name': asset.name,
                        'error': contract_result.get('error', '未知错误')
                    })
                    current_app.logger.error(f"资产 {asset.id} 合约地址生成失败")
                    
            except Exception as e:
                failed_assets.append({
                    'id': asset.id,
                    'name': asset.name,
                    'error': str(e)
                })
                current_app.logger.error(f"修复资产 {asset.id} 时发生异常: {str(e)}")
        
        # 提交所有更改
        db.session.commit()
        
        result = {
            'success': True,
            'message': f'批量修复完成，成功修复 {fixed_count} 个资产',
            'fixed_count': fixed_count,
            'total_count': len(assets_to_fix)
        }
        
        if failed_assets:
            result['failed_assets'] = failed_assets
            result['message'] += f'，{len(failed_assets)} 个资产修复失败'
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"批量修复合约地址失败: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f"批量修复失败: {str(e)}"
        }), 500

@admin_api_bp.route('/assets/fix-contract/<int:asset_id>', methods=['POST'])
@api_admin_required
def api_fix_asset_contract(asset_id):
    """修复单个资产的合约地址"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 检查资产是否需要修复
        if asset.token_address:
            return jsonify({
                'success': False,
                'error': '该资产已有合约地址'
            })
        
        # 使用区块链服务生成合约地址
        from app.blockchain.rwa_contract_service import rwa_contract_service
        import json
        
        contract_result = rwa_contract_service.create_asset_directly(
            creator_address=asset.creator_address,
            asset_name=asset.name,
            asset_symbol=asset.token_symbol,
            total_supply=asset.token_supply,
            decimals=0,
            price_per_token=asset.token_price
        )
        
        if contract_result['success']:
            # 更新资产信息
            asset.token_address = contract_result['mint_account']
            asset.blockchain_data = json.dumps(contract_result['blockchain_data'])
            asset.status = 2  # 确保状态为已通过
            asset.updated_at = datetime.now()
            
            db.session.commit()
            
            current_app.logger.info(f"资产 {asset_id} 合约地址修复成功: {asset.token_address}")
            
            return jsonify({
                'success': True,
                'message': '合约地址修复成功',
                'token_address': asset.token_address,
                'asset_id': asset_id
            })
        else:
            current_app.logger.error(f"资产 {asset_id} 合约地址生成失败: {contract_result.get('error')}")
            return jsonify({
                'success': False,
                'error': f"合约地址生成失败: {contract_result.get('error')}"
            })
            
    except Exception as e:
        current_app.logger.error(f"修复资产 {asset_id} 合约地址失败: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f"修复失败: {str(e)}"
        }), 500

@admin_api_bp.route('/assets/contract-status', methods=['GET'])
@api_admin_required
def api_assets_contract_status():
    """获取资产合约地址状态统计"""
    try:
        # 统计各种状态的资产数量
        total_assets = Asset.query.count()
        assets_with_contract = Asset.query.filter(
            Asset.token_address.isnot(None),
            Asset.token_address != ''
        ).count()
        assets_without_contract = total_assets - assets_with_contract
        
        # 统计状态为2但没有合约地址的资产
        approved_without_contract = Asset.query.filter(
            Asset.status == 2,
            or_(Asset.token_address.is_(None), Asset.token_address == '')
        ).count()
        
        pending_assets = Asset.query.filter_by(status=1).count()
        approved_assets = Asset.query.filter_by(status=2).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total_assets': total_assets,
                'assets_with_contract': assets_with_contract,
                'assets_without_contract': assets_without_contract,
                'approved_without_contract': approved_without_contract,
                'pending_assets': pending_assets,
                'approved_assets': approved_assets
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取资产合约状态统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取统计失败: {str(e)}"
        }), 500