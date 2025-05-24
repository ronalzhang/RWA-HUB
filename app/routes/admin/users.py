"""
用户管理模块
"""

from flask import render_template, jsonify
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required


@admin_bp.route('/users')
@admin_page_required
def users():
    """用户管理页面"""
    return render_template('admin/users.html')


@admin_bp.route('/v2/users')
@admin_page_required
def users_v2():
    """V2版本用户管理页面"""
    return render_template('admin/v2/users.html') 