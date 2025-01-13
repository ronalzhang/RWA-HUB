from flask import render_template, send_from_directory, current_app, request, redirect, url_for
from . import main_bp, auth_bp, assets_bp
from .admin import admin_required, is_admin

# 主页路由
@main_bp.route('/')
def index():
    return render_template('index.html')

# 静态文件路由
@main_bp.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(current_app.static_folder, filename)

# 认证页面路由
@auth_bp.route('/login')
def login():
    return render_template('auth/login.html')

@auth_bp.route('/register')
def register():
    return render_template('auth/register.html')

# 资产页面路由
@assets_bp.route('/')
def list_assets():
    return render_template('assets/list.html')

@assets_bp.route('/create')
def create_asset():
    return render_template('assets/create.html')

@assets_bp.route('/<int:asset_id>')
def asset_detail(asset_id):
    return render_template('assets/detail.html', asset_id=asset_id)

@assets_bp.route('/<int:asset_id>/edit')
def edit_asset(asset_id):
    """编辑资产页面
    
    Args:
        asset_id: 资产ID
        
    Returns:
        如果是管理员且资产未上链，返回编辑页面
        否则重定向到首页
    """
    # 从请求参数获取钱包地址和上链状态
    eth_address = request.args.get('eth_address')
    is_on_chain = request.args.get('is_on_chain') == 'true'
    
    # 记录请求参数
    print('编辑资产请求:', {
        'asset_id': asset_id,
        'eth_address': eth_address,
        'is_on_chain': is_on_chain
    })
    
    # 检查钱包地址
    if not eth_address:
        print('缺少钱包地址，重定向到首页')
        return redirect(url_for('main.index'))
    
    # 检查管理员权限
    if not is_admin(eth_address):
        print('非管理员访问，重定向到首页')
        return redirect(url_for('main.index'))
        
    # 如果资产已上链，重定向到首页
    if is_on_chain:
        print('已上链资产无法编辑，重定向到首页')
        return redirect(url_for('main.index'))
    
    # 渲染编辑页面
    return render_template('assets/edit.html', asset_id=asset_id)

# 管理页面路由
@assets_bp.route('/manage')
def manage_assets():
    return render_template('assets/manage.html') 