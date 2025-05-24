"""
仪表板管理模块
"""

from flask import render_template, jsonify
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required


@admin_bp.route('/dashboard')
@admin_page_required  
def dashboard():
    """仪表板页面"""
    return render_template('admin/dashboard.html')


@admin_bp.route('/v2/dashboard')
@admin_page_required
def dashboard_v2():
    """V2版本仪表板页面"""
    return render_template('admin/v2/dashboard.html')


@admin_bp.route('/v2')
@admin_page_required
def admin_v2_index():
    """V2版本管理后台首页"""
    return render_template('admin/v2/dashboard.html') 