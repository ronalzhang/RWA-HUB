import os
from qiniu import Auth, put_data, BucketManager
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class QiniuStorage:
    def __init__(self):
        self.access_key = current_app.config.get('QINIU_ACCESS_KEY')
        self.secret_key = current_app.config.get('QINIU_SECRET_KEY')
        self.bucket_name = current_app.config.get('QINIU_BUCKET_NAME')
        self.domain = current_app.config.get('QINIU_DOMAIN')
        
        # 记录配置信息
        logger.info(f"初始化七牛云存储:")
        logger.info(f"- Domain: {self.domain}")
        logger.info(f"- Bucket: {self.bucket_name}")
        logger.info(f"- Access Key: {'*' * len(self.access_key) if self.access_key else 'None'}")
        
        if not all([self.access_key, self.secret_key, self.bucket_name, self.domain]):
            missing = []
            if not self.access_key: missing.append('QINIU_ACCESS_KEY')
            if not self.secret_key: missing.append('QINIU_SECRET_KEY')
            if not self.bucket_name: missing.append('QINIU_BUCKET_NAME')
            if not self.domain: missing.append('QINIU_DOMAIN')
            error_msg = f"七牛云配置不完整，缺少: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        try:
            self.auth = Auth(self.access_key, self.secret_key)
            self.bucket = BucketManager(self.auth)
            logger.info("七牛云客户端初始化成功")
        except Exception as e:
            logger.error(f"七牛云客户端初始化失败: {str(e)}")
            raise
    
    def upload(self, file_data, filename):
        """上传文件到七牛云"""
        try:
            logger.info(f"开始上传文件: {filename}")
            
            # 生成上传凭证
            token = self.auth.upload_token(self.bucket_name)
            logger.info("成功生成上传凭证")
            
            # 上传文件
            ret, info = put_data(token, filename, file_data)
            
            logger.info(f"上传响应: status={info.status_code}, ret={ret}")
            
            if info.status_code == 200:
                # 构建文件URL
                file_url = f"http://{self.domain}/{ret['key']}"
                logger.info(f"文件上传成功: {file_url}")
                return file_url
            else:
                logger.error(f"文件上传失败: status={info.status_code}, error={info.error}")
                return None
                
        except Exception as e:
            logger.error(f"文件上传出错: {str(e)}")
            return None
    
    def delete(self, file_url):
        """从七牛云删除文件"""
        try:
            # 从URL中提取文件名
            key = file_url.split('/')[-1]
            logger.info(f"开始删除文件: {key}")
            
            # 删除文件
            ret, info = self.bucket.delete(self.bucket_name, key)
            
            if info.status_code == 200:
                logger.info(f"文件删除成功: {key}")
                return True
            else:
                logger.error(f"文件删除失败: status={info.status_code}, error={info.error}")
                return False
                
        except Exception as e:
            logger.error(f"文件删除出错: {str(e)}")
            return False

# 创建全局实例
storage = None

def init_storage():
    """初始化存储实例"""
    global storage
    try:
        logger.info("开始初始化七牛云存储...")
        storage = QiniuStorage()
        logger.info("七牛云存储初始化成功")
        return True
    except Exception as e:
        logger.error(f"七牛云存储初始化失败: {str(e)}")
        storage = None
        return False 
