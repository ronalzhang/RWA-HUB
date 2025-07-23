"""
数据验证管理路由
提供数据一致性检查和修复功能
"""

from flask import render_template, jsonify, current_app
from app.utils.data_validator import DataValidator
from . import admin_api_bp
from .auth import api_admin_required


@admin_api_bp.route('/data/validate', methods=['GET'])
@api_admin_required
def api_validate_data():
    """验证所有数据的一致性"""
    try:
        result = DataValidator.validate_all_assets()
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'数据验证失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/data/fix', methods=['POST'])
@api_admin_required
def api_fix_data():
    """自动修复数据一致性问题"""
    try:
        result = DataValidator.fix_asset_data_issues()
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'数据修复失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/data/status', methods=['GET'])
@api_admin_required
def api_data_status():
    """获取数据状态概览"""
    try:
        validation_result = DataValidator.validate_all_assets()
        
        # 构建状态汇总
        status = {
            'success': True,
            'data_health': 'healthy' if validation_result.get('total_issues', 0) == 0 else 'issues_found',
            'total_assets': validation_result.get('total_assets', 0),
            'valid_assets': validation_result.get('valid_assets', 0),
            'invalid_assets': validation_result.get('invalid_assets', 0),
            'total_issues': validation_result.get('total_issues', 0),
            'needs_attention': validation_result.get('total_issues', 0) > 0
        }
        
        return jsonify(status)
        
    except Exception as e:
        current_app.logger.error(f'获取数据状态失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500