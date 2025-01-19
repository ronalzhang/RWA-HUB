import os
from qiniu import Auth, put_data, BucketManager
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class QiniuStorage:
    def __init__(self):
        self.access_key = os.getenv('QINIU_ACCESS_KEY')
        self.secret_key = os.getenv('QINIU_SECRET_KEY')
        self.bucket_name = os.getenv('QINIU_BUCKET_NAME')
        self.domain = os.getenv('QINIU_DOMAIN')  # 您的七牛云域名
        
        if not all([self.access_key, self.secret_key, self.bucket_name, self.domain]):
            raise ValueError("七牛云配置不完整")
            
        self.auth = Auth(self.access_key, self.secret_key)
        self.bucket = BucketManager(self.auth)
    
    def upload(self, file_data, filename):
        """上传文件到七牛云"""
        try:
            # 生成上传凭证
            token = self.auth.upload_token(self.bucket_name)
            
            # 上传文件
            ret, info = put_data(token, filename, file_data)
            
            if info.status_code == 200:
                # 返回文件的访问URL
                return f"https//{self.domain}/{ret['key']}"
            else:
                logger.error(f"文件上传失败: {info}")
                return None
                
        except Exception as e:
            logger.error(f"文件上传出错: {e}")
            return None
    
    def delete(self, file_url):
        """从七牛云删除文件"""
        try:
            # 从URL中提取文件名
            key = file_url.split('/')[-1]
            
            # 删除文件
            ret, info = self.bucket.delete(self.bucket_name, key)
            
            if info.status_code == 200:
                return True
            else:
                logger.error(f"文件删除失败: {info}")
                return False
                
        except Exception as e:
            logger.error(f"文件删除出错: {e}")
            return False

# 创建全局实例
storage = None

def init_storage():
    """初始化存储实例"""
    global storage
    try:
        storage = QiniuStorage()
        logger.info("七牛云存储初始化成功")
    except Exception as e:
        logger.error(f"七牛云存储初始化失败: {e}")
        storage = None 
