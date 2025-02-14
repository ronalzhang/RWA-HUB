import os
from qiniu import Auth, put_data, BucketManager
from flask import current_app
import logging
import time
from werkzeug.utils import secure_filename
import qiniu

logger = logging.getLogger(__name__)

class QiniuStorage:
    def __init__(self, access_key, secret_key, bucket_name, domain):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.domain = domain
        
        if not all([self.access_key, self.secret_key, self.bucket_name, self.domain]):
            raise ValueError("七牛云配置不完整")
            
        try:
            self.auth = Auth(self.access_key, self.secret_key)
            self.bucket = BucketManager(self.auth)
            logger.info("七牛云存储初始化成功")
        except Exception as e:
            logger.error(f"七牛云存储初始化失败: {str(e)}")
            raise
    
    def upload(self, file_data, key):
        """上传文件到七牛云"""
        try:
            if not file_data:
                raise ValueError("文件数据为空")
                
            # 生成上传凭证
            token = self.auth.upload_token(self.bucket_name)
            
            # 上传文件
            ret, info = put_data(token, key, file_data)
            
            if info.status_code == 200:
                # 使用 HTTP 协议
                domain = self.domain
                if domain.startswith('https://'):
                    domain = 'http://' + domain[8:]
                elif not domain.startswith('http://'):
                    domain = 'http://' + domain
                    
                # 生成完整的URL，保留文件路径
                url = f"{domain}/{ret['key']}"
                
                # 确保URL使用HTTP协议
                if url.startswith('https://'):
                    url = 'http://' + url[8:]
                
                return {
                    'url': url,
                    'key': ret['key'],
                    'name': key.split('/')[-1]  # 只返回文件名部分
                }
            else:
                logger.error(f"上传失败: {info.error}")
                return None
                
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            return None

    def delete(self, key):
        """删除文件"""
        try:
            ret, info = self.bucket.delete(self.bucket_name, key)
            return info.status_code == 200
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False

# 创建全局实例
storage = None

def init_storage(app):
    """初始化存储实例"""
    global storage
    
    # 如果已经初始化，直接返回
    if storage is not None:
        return True
        
    try:
        with app.app_context():
            logger.info("开始初始化七牛云存储...")
            
            # 从配置中获取七牛云参数
            access_key = app.config.get('QINIU_ACCESS_KEY')
            secret_key = app.config.get('QINIU_SECRET_KEY')
            bucket_name = app.config.get('QINIU_BUCKET_NAME')
            domain = app.config.get('QINIU_DOMAIN')
            
            # 如果配置中没有，使用默认值
            if not all([access_key, secret_key, bucket_name, domain]):
                access_key = 'SGMhwmXf7wRlmsgXU4xfqzDH_DxczWhhoDEjyYE9'
                secret_key = '6JynlQeJEDWt4VIjZV8sDdSAFZMrZ3GFE0fIz07-'
                bucket_name = 'rwa-hub'
                domain = 'sqbw3uvy8.sabkt.gdipper.com'
                logger.info("使用默认七牛云配置")
            
            # 创建存储实例
            storage = QiniuStorage(
                access_key=access_key,
                secret_key=secret_key,
                bucket_name=bucket_name,
                domain=domain
            )
            
            # 测试上传以验证配置是否正确
            test_result = storage.upload(b"test", "test.txt")
            if not test_result:
                raise ValueError("存储配置测试失败")
            
            # 删除测试文件
            storage.delete("test.txt")
            
            logger.info("七牛云存储初始化成功")
            return True
            
    except Exception as e:
        logger.error(f"七牛云存储初始化失败: {str(e)}")
        storage = None
        return False

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
        filename = secure_filename(file.filename)
        
        # 读取文件数据
        file_data = file.read()
        
        # 上传到存储服务
        result = storage.upload(file_data, filename)
        if result:
            current_app.logger.info(f'文件上传成功: {result}')
            return result
            
        return None
        
    except Exception as e:
        current_app.logger.error(f'文件上传处理失败: {str(e)}')
        return None 