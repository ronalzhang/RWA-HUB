from flask import render_template
from . import main_bp

@main_bp.route('/')
def index():
    """首页"""
    return render_template('index.html')

@main_bp.route('/auth/login')
def login():
    """登录页面"""
    return render_template('auth/login.html')

@main_bp.route('/auth/register')
def register():
    """注册页面"""
    return render_template('auth/register.html') 