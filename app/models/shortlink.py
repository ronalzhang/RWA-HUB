import datetime
import random
import string
from app.models import db

def generate_unique_code(length=6):
    """生成随机的短链接代码"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

class ShortLink(db.Model):
    """短链接模型"""
    __tablename__ = 'short_links'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, index=True, nullable=False)
    original_url = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    click_count = db.Column(db.Integer, default=0)
    creator_address = db.Column(db.String(128), nullable=True)  # 创建者钱包地址
    
    @classmethod
    def create_short_link(cls, original_url, creator_address=None, expires_days=None):
        """创建新的短链接"""
        while True:
            code = generate_unique_code()
            # 检查代码是否已存在
            existing = cls.query.filter_by(code=code).first()
            if not existing:
                break
        
        expires_at = None
        if expires_days:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)
        
        short_link = cls(
            code=code,
            original_url=original_url,
            creator_address=creator_address,
            expires_at=expires_at
        )
        
        db.session.add(short_link)
        db.session.commit()
        
        return short_link
    
    def increment_click(self):
        """增加点击计数"""
        self.click_count += 1
        db.session.commit()
    
    def is_expired(self):
        """检查链接是否过期"""
        if not self.expires_at:
            return False
        return datetime.datetime.utcnow() > self.expires_at
    
    def to_dict(self):
        """转换为字典表示"""
        return {
            'code': self.code,
            'original_url': self.original_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'click_count': self.click_count
        } 