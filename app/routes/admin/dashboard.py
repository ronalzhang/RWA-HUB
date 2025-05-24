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
    return render_template('admin/v2/dashboard.html')


@admin_bp.route('/')
@admin_page_required
def admin_index():
    """管理后台首页"""
    return render_template('admin/v2/dashboard.html') 