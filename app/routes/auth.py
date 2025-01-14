from flask import render_template, Blueprint

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    """登录页面"""
    return render_template('auth/login.html')

@auth_bp.route('/register')
def register():
    """注册页面"""
    return render_template('auth/register.html')