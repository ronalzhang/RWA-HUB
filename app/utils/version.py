import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def get_version():
    """获取应用版本号"""
    version = os.getenv('APP_VERSION', '1.0.0')
    return {
        'version': version,
        'environment': os.getenv('FLASK_ENV', 'development'),
        'debug': current_app.debug
    }

def save_files(files, asset_type, asset_id):
    """保存上传的文件
    
    Args:
        files: 文件列表
        asset_type: 资产类型 (real_estate 或 quasi_real_estate)
        asset_id: 资产ID
        
    Returns:
        保存的文件路径列表
    """
    if not files:
        return []
        
    # 确保目录存在
    upload_dir = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        asset_type.lower(),
        str(asset_id)
    )
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_paths = []
    for file in files:
        if file:
            # 生成安全的文件名
            filename = secure_filename(file.filename)
            # 添加UUID前缀避免重名
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            # 构建保存路径
            save_path = os.path.join(upload_dir, unique_filename)
            # 保存文件
            file.save(save_path)
            # 记录相对路径
            relative_path = os.path.join(
                'static',
                'uploads',
                asset_type.lower(),
                str(asset_id),
                unique_filename
            )
            saved_paths.append(relative_path)
            
    return saved_paths 