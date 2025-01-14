from flask import render_template, send_from_directory, current_app, abort, request, redirect, url_for, jsonify, Blueprint
from ..models import db, Asset
from ..utils import is_admin, save_files
import os

assets_bp = Blueprint('assets', __name__)

# 页面路由
@assets_bp.route("/")
def list_assets():
    """资产列表页面"""
    return render_template("assets/list.html")

@assets_bp.route("/<int:asset_id>")
def asset_detail(asset_id):
    """资产详情页面"""
    return render_template("assets/detail.html", asset_id=asset_id)

@assets_bp.route("/create")
def create_asset_page():
    """创建资产页面"""
    return render_template("assets/create.html")

@assets_bp.route("/<int:asset_id>/edit")
def edit_asset_page(asset_id):
    eth_address = request.headers.get('X-Eth-Address')
    current_app.logger.info(f"编辑资产请求: {{'asset_id': {asset_id}, 'eth_address': {eth_address}, 'is_on_chain': False}}")
    
    if not eth_address:
        current_app.logger.warning("缺少钱包地址，重定向到首页")
        return redirect('/')
        
    if not is_admin(eth_address):
        current_app.logger.warning(f"非管理员用户({eth_address})尝试编辑资产")
        return redirect('/')
        
    return render_template('assets/edit.html')

@assets_bp.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    """提供上传文件的访问"""
    try:
        # 获取上传目录
        uploads_dir = current_app.config['UPLOAD_FOLDER']
        current_app.logger.info(f"上传目录: {uploads_dir}")
        
        # 构建完整的文件路径
        file_path = os.path.abspath(os.path.join(uploads_dir, filename))
        current_app.logger.info(f"请求的文件路径: {file_path}")
        
        # 安全检查：确保文件路径在上传目录内
        if not file_path.startswith(uploads_dir):
            current_app.logger.error(f"安全检查失败: {file_path} 不在 {uploads_dir} 内")
            abort(404)
            
        # 检查文件是否存在
        if os.path.exists(file_path):
            current_app.logger.info(f"文件存在，准备发送: {file_path}")
            # 获取文件所在的目录
            directory = os.path.dirname(file_path)
            # 获取文件名
            basename = os.path.basename(file_path)
            current_app.logger.info(f"发送文件: 目录={directory}, 文件名={basename}")
            return send_from_directory(directory, basename)
            
        current_app.logger.error(f"文件不存在: {file_path}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"处理文件访问时出错 {filename}: {str(e)}")
        abort(404)
