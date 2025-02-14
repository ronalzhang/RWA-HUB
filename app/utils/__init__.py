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
    import time
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 1  # 重试延迟（秒）
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    # 检查存储服务
    if storage is None:
        current_app.logger.error('七牛云存储服务未初始化')
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
            failed_files.append({
                'name': f'file_{i}',
                'error': '无效的文件'
            })
            continue
            
        if not allowed_file(file.filename):
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
                timestamp = int(time.time() * 1000)  # 使用毫秒级时间戳
                filename = f'{asset_type}/{asset_id}/file_{timestamp}_{i+1}{ext}'
                
                current_app.logger.info(f'处理文件 {i+1}/{len(files)}: {filename}')
                
                # 读取文件内容
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
                if file_size > 100 * 1024 * 1024:  # 100MB
                    current_app.logger.error(f'文件大小超过限制: {filename} ({file_size} bytes)')
                    failed_files.append({
                        'name': file.filename,
                        'error': '文件大小超过限制(100MB)'
                    })
                    break
                
                # 上传到七牛云
                current_app.logger.info(f'尝试上传文件 (第{retry_count + 1}次): {filename}')
                result = storage.upload(file_data, filename)
                
                if result and result.get('url'):
                    file_urls.append(result['url'])
                    current_app.logger.info(f'文件上传成功: {result["url"]}')
                    break
                else:
                    raise Exception("七牛云返回空URL")
                    
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