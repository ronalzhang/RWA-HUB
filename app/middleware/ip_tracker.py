from flask import request, g
from app.models import IPVisit
from app.extensions import db
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class IPTracker:
    """IP访问追踪中间件"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用"""
        app.before_request(self.before_request)
    
    def get_real_ip(self):
        """获取真实IP地址（考虑代理和负载均衡）"""
        # 优先级：X-Forwarded-For > X-Real-IP > X-Forwarded > remote_addr
        if request.headers.get('X-Forwarded-For'):
            # X-Forwarded-For可能包含多个IP，取第一个
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            ip = request.headers.get('X-Real-IP').strip()
        elif request.headers.get('X-Forwarded'):
            ip = request.headers.get('X-Forwarded').strip()
        else:
            ip = request.remote_addr
        
        return ip
    
    def should_track(self):
        """判断是否应该记录此次访问"""
        # 排除静态资源和API调用
        excluded_paths = [
            '/static/',
            '/favicon.ico',
            '/robots.txt',
            '/sitemap.xml',
            '/admin/api/',  # 排除管理API调用
        ]
        
        # 排除特定文件扩展名
        excluded_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf']
        
        path = request.path.lower()
        
        # 检查排除路径
        for excluded_path in excluded_paths:
            if path.startswith(excluded_path):
                return False
        
        # 检查文件扩展名
        for ext in excluded_extensions:
            if path.endswith(ext):
                return False
        
        return True
    
    def before_request(self):
        """请求前处理"""
        try:
            # 检查是否应该记录
            if not self.should_track():
                return
            
            # 获取IP地址
            ip_address = self.get_real_ip()
            
            # 获取其他信息
            user_agent = request.headers.get('User-Agent', '')
            referer = request.headers.get('Referer', '')
            path = request.path
            
            # 获取中国时区的当前时间
            china_tz = pytz.timezone('Asia/Shanghai')
            current_time = datetime.now(china_tz).replace(tzinfo=None)  # 移除时区信息以匹配数据库字段
            
            # 创建访问记录
            visit = IPVisit(
                ip_address=ip_address,
                user_agent=user_agent[:1000] if user_agent else None,  # 限制长度
                referer=referer[:500] if referer else None,  # 限制长度
                path=path[:500] if path else None,  # 限制长度
                timestamp=current_time
            )
            
            # 保存到数据库
            db.session.add(visit)
            db.session.commit()
            
            # 存储到g对象供后续使用
            g.current_visit = visit
            
        except Exception as e:
            # 记录错误但不影响正常请求
            logger.error(f"IP访问记录失败: {e}")
            db.session.rollback()

# 创建全局实例
ip_tracker = IPTracker() 