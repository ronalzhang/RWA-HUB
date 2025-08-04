from flask import g, current_app
import os
from werkzeug.utils import secure_filename
from .decorators import (
    handle_api_errors, 
    require_wallet_address, 
    require_admin_wallet, 
    api_endpoint
)
from .admin import is_admin, get_admin_permissions, has_permission
from .storage import storage, init_storage, get_storage

# For backward compatibility, create aliases
admin_required = require_admin_wallet
eth_address_required = require_wallet_address

__all__ = [
    'handle_api_errors',
    'require_wallet_address',
    'require_admin_wallet',
    'api_endpoint',
    'admin_required',
    'eth_address_required',
    'is_admin',
    'get_admin_permissions',
    'has_permission'
]

def save_files(files, asset_type, asset_id, token_symbol=None):
    """保存上传的文件到本地存储
    
    Args:
        files: 文件列表
        asset_type: 资产类型 (real_estate 或 quasi_real_estate)
        asset_id: 资产ID
        token_symbol: 代币符号 (可选)
        
    Returns:
        保存的文件 URL 列表
    """
    import time
    import os
    import shutil
    from werkzeug.utils import secure_filename
    from flask import current_app
    from .storage import get_storage
    
    # 允许的文件扩展名 - 添加webp格式
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx'}
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 1  # 重试延迟（秒）
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    # 获取存储服务实例
    try:
        storage = get_storage()
        if not storage:
            current_app.logger.error('存储服务初始化失败')
            # 尝试再次初始化
            from .storage import init_storage
            init_storage(current_app)
            storage = get_storage()
            if not storage:
                raise ValueError('存储服务未准备就绪')
    except Exception as e:
        current_app.logger.error(f'获取存储服务失败: {str(e)}')
        # 使用本地存储方式
        try:
            from .storage import LocalStorage
            upload_folder = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            storage = LocalStorage(upload_folder)
            current_app.logger.info('已创建临时本地存储实例')
        except Exception as inner_e:
            current_app.logger.error(f'创建临时存储实例失败: {str(inner_e)}')
            raise ValueError('存储服务未准备就绪')
    
    # 检查参数
    if not files:
        current_app.logger.error('没有提供文件')
        raise ValueError('没有提供文件')
        
    if not asset_type:
        current_app.logger.error('没有提供资产类型')
        raise ValueError('没有提供资产类型')
        
    if not asset_id:
        current_app.logger.error('没有提供资产ID')
        raise ValueError('没有提供资产ID')
    
    # 保存文件
    file_urls = []
    failed_files = []
    
    current_app.logger.info(f'开始处理 {len(files)} 个文件')
    
    for i, file in enumerate(files):
        if not file or not file.filename:
            current_app.logger.error(f'文件 {i} 无效')
            failed_files.append({
                'name': f'file_{i}',
                'error': '无效的文件'
            })
            continue
            
        current_app.logger.info(f'处理文件 {i+1}: {file.filename}')
            
        if not allowed_file(file.filename):
            current_app.logger.error(f'文件类型不支持: {file.filename}')
            failed_files.append({
                'name': file.filename,
                'error': '不支持的文件类型'
            })
            continue
            
        retry_count = 0
        last_error = None
        
        while retry_count < MAX_RETRIES:
            try:
                # 构建文件名
                ext = os.path.splitext(secure_filename(file.filename))[1]
                timestamp = int(time.time())  # 使用秒级时间戳，便于调试
                
                # 根据是否提供token_symbol决定文件路径
                if token_symbol:
                    # 使用项目目录结构
                    file_type = 'images' if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else 'documents'
                    filename = f"projects/{token_symbol}/{file_type}/{timestamp}_{secure_filename(file.filename)}"
                    current_app.logger.info(f'使用新目录结构: {filename}')
                else:
                    # 使用旧的目录结构
                    file_type = 'image' if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else 'document'
                    filename = f"{asset_id}/temp/{file_type}/{timestamp}_{secure_filename(file.filename)}"
                    current_app.logger.info(f'使用旧目录结构: {filename}')
                
                current_app.logger.info(f'处理文件 {i+1}/{len(files)}: {filename}')
                
                # 读取文件内容（只读取一次）
                if retry_count == 0:
                    file_data = file.read()
                    if not file_data:
                        current_app.logger.error(f'文件内容为空: {filename}')
                        failed_files.append({
                            'name': file.filename,
                            'error': '文件内容为空'
                        })
                        break
                    
                    # 检查文件大小
                    file_size = len(file_data)
                    current_app.logger.info(f'文件大小: {file_size} bytes')
                    
                    if file_size > 20 * 1024 * 1024:  # 20MB
                        current_app.logger.error(f'文件大小超过限制: {filename} ({file_size} bytes)')
                        failed_files.append({
                            'name': file.filename,
                            'error': '文件大小超过限制(20MB)'
                        })
                        break
                
                # 确保目录存在
                target_dir = os.path.join(current_app.static_folder, 'uploads', os.path.dirname(filename))
                os.makedirs(target_dir, exist_ok=True)
                
                # 上传到本地存储
                current_app.logger.info(f'尝试上传文件 (第{retry_count + 1}次): {filename}')
                
                # 首先尝试使用storage服务
                result = storage.upload(file_data, filename)
                
                if result and result.get('url'):
                    # 存储服务上传成功
                    file_urls.append(result['url'])
                    current_app.logger.info(f'文件上传成功: {result["url"]}')
                    break
                else:
                    # 存储服务失败，尝试直接保存到本地文件系统
                    current_app.logger.warning(f'存储服务失败，尝试直接保存到本地')
                    full_path = os.path.join(target_dir, os.path.basename(filename))
                    with open(full_path, 'wb') as f:
                        f.write(file_data)
                    
                    # 构建URL
                    url = f'/static/uploads/{filename}'
                    file_urls.append(url)
                    current_app.logger.info(f'文件保存成功: {url}')
                    break
                    
            except Exception as e:
                last_error = str(e)
                current_app.logger.error(f'上传失败 (第{retry_count + 1}次): {str(e)}')
                retry_count += 1
                
                if retry_count < MAX_RETRIES:
                    current_app.logger.info(f'等待 {RETRY_DELAY} 秒后重试...')
                    time.sleep(RETRY_DELAY)
                else:
                    failed_files.append({
                        'name': file.filename,
                        'error': f'上传失败: {last_error}'
                    })
                    
            finally:
                # 确保文件指针回到开始位置，以便重试
                file.seek(0)
    
    # 返回结果
    if failed_files:
        current_app.logger.warning(f'部分文件上传失败: {failed_files}')
    
    current_app.logger.info(f'文件上传完成，成功: {len(file_urls)}，失败: {len(failed_files)}')
    return file_urls

def move_temp_files_to_project(asset_id, token_symbol):
    """
    将临时目录中的文件移动到项目目录
    
    Args:
        asset_id: 资产ID
        token_symbol: 代币符号
    
    Returns:
        移动成功的文件URL列表
    """
    import os
    import shutil
    from flask import current_app
    
    if not token_symbol:
        current_app.logger.error('没有提供代币符号，无法移动文件')
        return []
    
    # 获取上传根目录
    upload_folder = os.path.join(current_app.static_folder, 'uploads')
    
    # 临时目录
    temp_image_dir = os.path.join(upload_folder, f"{asset_id}/temp/image")
    temp_document_dir = os.path.join(upload_folder, f"{asset_id}/temp/document")
    
    # 项目目录
    project_image_dir = os.path.join(upload_folder, f"projects/{token_symbol}/images")
    project_document_dir = os.path.join(upload_folder, f"projects/{token_symbol}/documents")
    
    # 确保项目目录存在
    os.makedirs(project_image_dir, exist_ok=True)
    os.makedirs(project_document_dir, exist_ok=True)
    
    moved_files = []
    
    # 移动图片
    if os.path.exists(temp_image_dir):
        current_app.logger.info(f'准备移动临时图片从 {temp_image_dir} 到 {project_image_dir}')
        try:
            for filename in os.listdir(temp_image_dir):
                src_path = os.path.join(temp_image_dir, filename)
                dst_path = os.path.join(project_image_dir, filename)
                
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)  # 复制而不是移动，保留原始文件
                    moved_files.append(f'/static/uploads/projects/{token_symbol}/images/{filename}')
                    current_app.logger.info(f'成功复制文件: {src_path} -> {dst_path}')
        except Exception as e:
            current_app.logger.error(f'移动图片时出错: {str(e)}')
    else:
        current_app.logger.warning(f'临时图片目录不存在: {temp_image_dir}')
    
    # 移动文档
    if os.path.exists(temp_document_dir):
        current_app.logger.info(f'准备移动临时文档从 {temp_document_dir} 到 {project_document_dir}')
        try:
            for filename in os.listdir(temp_document_dir):
                src_path = os.path.join(temp_document_dir, filename)
                dst_path = os.path.join(project_document_dir, filename)
                
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)  # 复制而不是移动，保留原始文件
                    moved_files.append(f'/static/uploads/projects/{token_symbol}/documents/{filename}')
                    current_app.logger.info(f'成功复制文件: {src_path} -> {dst_path}')
        except Exception as e:
            current_app.logger.error(f'移动文档时出错: {str(e)}')
    else:
        current_app.logger.warning(f'临时文档目录不存在: {temp_document_dir}')
    
    current_app.logger.info(f'总共移动了 {len(moved_files)} 个文件到项目目录')
    return moved_files