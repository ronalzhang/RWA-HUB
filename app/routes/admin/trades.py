"""
交易管理模块
"""

from flask import render_template, jsonify
from . import admin_bp, admin_api_bp
from .auth import api_admin_required, admin_page_required


@admin_bp.route('/trades')
@admin_page_required
def trades():
    """交易管理页面"""
    return render_template('admin/trades.html')


@admin_bp.route('/v2/trades')
@admin_page_required
def trades_v2():
    """V2版本交易管理页面"""
    return render_template('admin/v2/trades.html') 