from datetime import datetime
from app.extensions import db

class IPVisit(db.Model):
    """IP访问记录模型"""
    __tablename__ = 'ip_visits'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # 支持IPv6
    user_agent = db.Column(db.Text)  # 浏览器信息
    referer = db.Column(db.String(500))  # 来源页面
    path = db.Column(db.String(500))  # 访问路径
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    country = db.Column(db.String(100))  # 国家（可选）
    city = db.Column(db.String(100))  # 城市（可选）
    
    # 复合索引优化查询性能
    __table_args__ = (
        db.Index('idx_ip_timestamp', 'ip_address', 'timestamp'),
        db.Index('idx_timestamp_desc', 'timestamp', postgresql_using='btree'),
    )
    
    def __repr__(self):
        return f'<IPVisit {self.ip_address} at {self.timestamp}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'referer': self.referer,
            'path': self.path,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'country': self.country,
            'city': self.city
        } 