from flask import render_template, Blueprint, jsonify

main_bp = Blueprint('main', __name__)

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

@main_bp.route('/health')
def health_check():
    """健康检查接口"""
    return jsonify({"status": "healthy"}), 200 