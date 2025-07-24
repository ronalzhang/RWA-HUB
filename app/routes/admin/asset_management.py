#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资产管理路由
提供资产合约地址修复等管理功能
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from app.models.asset import Asset
from app.extensions import db
from app.utils.auth import admin_required
import json
from datetime import datetime

# 创建蓝图
asset_management_bp = Blueprint('asset_management', __name__, url_prefix='/admin/assets')

@asset_management_bp.route('/contract-fix')
@admin_required
def contract_fix_page():
    """合约地址修复页面"""
    try:
        # 查询需要修复的资产（没有token_address的资产）
        assets_without_contract = Asset.query.filter(
            (Asset.token_address.is_(None)) | (Asset.token_address == '')
        ).filter(
            Asset.status.in_([1, 2])  # 只处理待审核或已通过的资产
        ).order_by(Asset.id).all()
        
        return render_template('admin/asset_contract_fix.html', 
                             assets=assets_without_contract)
    except Exception as e:
        current_app.logger.error(f"加载合约修复页面失败: {str(e)}")
        return f"加载页面失败: {str(e)}", 500

@asset_management_bp.route('/fix-contract/<int:asset_id>', methods=['POST'])
@admin_required
def fix_asset_contract(asset_id):
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
            asset.status = 2  # 设置为已通过状态
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
        })

@asset_management_bp.route('/fix-all-contracts', methods=['POST'])
@admin_required
def fix_all_contracts():
    """批量修复所有资产的合约地址"""
    try:
        # 查询需要修复的资产
        assets_to_fix = Asset.query.filter(
            (Asset.token_address.is_(None)) | (Asset.token_address == '')
        ).filter(
            Asset.status.in_([1, 2])  # 只处理待审核或已通过的资产
        ).all()
        
        if not assets_to_fix:
            return jsonify({
                'success': True,
                'message': '没有需要修复的资产',
                'fixed_count': 0
            })
        
        from app.blockchain.rwa_contract_service import rwa_contract_service
        
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
                    asset.status = 2  # 设置为已通过状态
                    asset.updated_at = datetime.now()
                    
                    fixed_count += 1
                    current_app.logger.info(f"资产 {asset.id} 合约地址修复成功")
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
        })

@asset_management_bp.route('/assets-status')
@admin_required
def assets_status():
    """获取资产状态统计"""
    try:
        # 统计各种状态的资产数量
        total_assets = Asset.query.count()
        assets_with_contract = Asset.query.filter(
            Asset.token_address.isnot(None),
            Asset.token_address != ''
        ).count()
        assets_without_contract = total_assets - assets_with_contract
        
        pending_assets = Asset.query.filter_by(status=1).count()
        approved_assets = Asset.query.filter_by(status=2).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total_assets': total_assets,
                'assets_with_contract': assets_with_contract,
                'assets_without_contract': assets_without_contract,
                'pending_assets': pending_assets,
                'approved_assets': approved_assets
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取资产状态统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"获取统计失败: {str(e)}"
        })