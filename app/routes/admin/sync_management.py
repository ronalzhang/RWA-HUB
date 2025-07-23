#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
同步管理API - 管理区块链数据同步服务
"""

from flask import Blueprint, request, jsonify, current_app
import logging
from app.utils.decorators import admin_required
from app.services.blockchain_sync_service import get_sync_service
from app.services.data_consistency_manager import DataConsistencyManager

logger = logging.getLogger(__name__)

# 创建蓝图
sync_management_bp = Blueprint('sync_management', __name__, url_prefix='/admin/v2/sync')

@sync_management_bp.route('/status', methods=['GET'])
@admin_required
def get_sync_status():
    """获取同步服务状态"""
    try:
        sync_service = get_sync_service()
        status = sync_service.get_sync_status()
        
        return jsonify({
            'success': True,
            'status': status
        }), 200
        
    except Exception as e:
        logger.error(f"获取同步状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_management_bp.route('/asset/<int:asset_id>/sync', methods=['POST'])
@admin_required
def force_sync_asset(asset_id):
    """强制同步指定资产"""
    try:
        sync_service = get_sync_service()
        result = sync_service.force_sync_asset(asset_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"强制同步资产失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_management_bp.route('/validate/<int:asset_id>', methods=['GET'])
@admin_required
def validate_asset_consistency(asset_id):
    """验证资产数据一致性"""
    try:
        data_manager = DataConsistencyManager()
        result = data_manager.validate_data_consistency(asset_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"验证数据一致性失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_management_bp.route('/cache/clear', methods=['POST'])
@admin_required
def clear_cache():
    """清除所有缓存"""
    try:
        data_manager = DataConsistencyManager()
        data_manager.clear_all_cache()
        
        return jsonify({
            'success': True,
            'message': '缓存已清除'
        }), 200
        
    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_management_bp.route('/assets/validate-all', methods=['POST'])
@admin_required
def validate_all_assets():
    """验证所有资产的数据一致性"""
    try:
        from app.models import Asset
        from app.models.asset import AssetStatus
        
        data_manager = DataConsistencyManager()
        
        # 获取所有活跃资产
        assets = Asset.query.filter(
            Asset.status.in_([AssetStatus.ON_CHAIN.value, AssetStatus.CONFIRMED.value]),
            Asset.deleted_at.is_(None)
        ).all()
        
        results = []
        total_issues = 0
        
        for asset in assets:
            try:
                result = data_manager.validate_data_consistency(asset.id)
                if result['success']:
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.name,
                        'issues_found': result['issues_found'],
                        'issues': result['issues']
                    })
                    total_issues += result['issues_found']
                else:
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.name,
                        'error': result['error']
                    })
            except Exception as e:
                results.append({
                    'asset_id': asset.id,
                    'asset_name': asset.name,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'total_assets': len(assets),
            'total_issues': total_issues,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"验证所有资产失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500