from flask import g, current_app
import os
from werkzeug.utils import secure_filename
from .decorators import token_required, eth_address_required 

def is_admin(eth_address=None):
    """检查指定地址或当前用户是否是管理员"""
    admin_addresses = [
        '0x6394993426DBA3b654eF0052698Fe9E0B6A98870',
        '0x124e5B8A4E6c68eC66e181E0B54817b12D879c57',
        '0x7EF71020630Ee5141F772c8a054d43A88A6919c7'
    ]
    
    if eth_address:
        return eth_address.lower() in [addr.lower() for addr in admin_addresses]
    return hasattr(g, 'eth_address') and g.eth_address.lower() in [addr.lower() for addr in admin_addresses] 

def save_files(files, asset_type, asset_id):
    """保存上传的文件
    
    Args:
        files: 文件列表
        asset_type: 资产类型 (real_estate 或 quasi_real_estate)
        asset_id: 资产ID
        
    Returns:
        保存的文件路径列表
    """
    # 创建资产目录
    asset_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], asset_type, str(asset_id))
    os.makedirs(asset_dir, exist_ok=True)
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    # 保存文件
    file_paths = []
    for i, file in enumerate(files):
        if file and allowed_file(file.filename):
            ext = os.path.splitext(secure_filename(file.filename))[1]
            filename = f'file_{i+1}{ext}'
            file_path = os.path.join(asset_dir, filename)
            file.save(file_path)
            file_paths.append(os.path.join('static', 'uploads', asset_type, str(asset_id), filename))
            
    return file_paths 