"""
佣金管理模块
"""

from flask import render_template, jsonify
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required


@admin_bp.route('/commission')
@admin_page_required
def commission():
    """佣金管理页面"""
    return render_template('admin/commission.html') 