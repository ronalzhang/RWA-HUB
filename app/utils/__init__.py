from flask import g, current_app
import os
from werkzeug.utils import secure_filename
from .decorators import token_required, eth_address_required, admin_required, permission_required
from .admin import is_admin, get_admin_permissions, has_permission

__all__ = [
    'token_required',
    'eth_address_required',
    'admin_required',
    'permission_required',
    'is_admin',
    'get_admin_permissions',
    'has_permission'
]

def save_files(files, asset_type, asset_id):
    """保存上传的文件到七牛云
    
    Args:
        files: 文件列表
        asset_type: 资产类型 (real_estate 或 quasi_real_estate)
        asset_id: 资产ID
        
    Returns:
        保存的文件 URL 列表
    """
    from .storage import storage
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    # 保存文件
    file_urls = []
    for i, file in enumerate(files):
        if file and allowed_file(file.filename):
            try:
                # 构建文件名
                ext = os.path.splitext(secure_filename(file.filename))[1]
                filename = f'{asset_type}/{asset_id}/file_{i+1}{ext}'
                
                # 读取文件内容
                file_data = file.read()
                
                # 上传到七牛云
                if storage is None:
                    raise Exception("七牛云存储未初始化")
                    
                url = storage.upload(file_data, filename)
                if url:
                    file_urls.append(url)
                    current_app.logger.info(f'上传文件成功: {url}')
                else:
                    raise Exception("七牛云上传失败")
                    
            except Exception as e:
                current_app.logger.error(f'上传文件失败: {str(e)}')
                continue
            
    return file_urls