import os
import logging
from werkzeug.utils import secure_filename
from flask import current_app
import time

logger = logging.getLogger(__name__)

class LocalStorage:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
    def upload(self, file_data, key):
        try:
            # 确保目录存在
            file_dir = os.path.join(self.upload_folder, os.path.dirname(key))
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            
            # 保存文件
            file_path = os.path.join(self.upload_folder, key)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # 返回相对路径
            return {
                'url': f'/static/uploads/{key}',
                'key': key
            }
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            return None

    def delete(self, key):
        try:
            file_path = os.path.join(self.upload_folder, key)
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False

# 创建全局实例
storage = None

def init_storage(app):
    """初始化存储实例"""
    global storage
    try:
        # 使用本地存储
        upload_folder = os.path.join(app.static_folder, 'uploads')
        storage = LocalStorage(upload_folder)
        logger.info("本地存储初始化成功")
        return True
    except Exception as e:
        logger.error(f"存储初始化失败: {str(e)}")
        return False

def get_storage():
    """获取存储服务实例"""
    global storage
    if storage is None:
        if not init_storage(current_app):
            raise ValueError("存储服务初始化失败")
    return storage

def upload_file(file):
    """统一的文件上传处理函数"""
    try:
        if not file:
            return None
            
        # 确保storage已初始化
        if not storage:
            init_storage(current_app)
            
        if not storage:
            current_app.logger.error('存储服务未初始化')
            return None
            
        # 生成安全的文件名
        timestamp = int(time.time() * 1000)
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        
        # 读取文件数据
        file_data = file.read()
        
        # 上传到存储服务
        result = storage.upload(file_data, f"uploads/{filename}")
        if result:
            current_app.logger.info(f'文件上传成功: {result}')
            return result
            
        return None
        
    except Exception as e:
        current_app.logger.error(f'文件上传处理失败: {str(e)}')
        return None 