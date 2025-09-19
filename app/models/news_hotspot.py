"""
新闻热点数据模型
"""
from datetime import datetime
from app.extensions import db
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index


class NewsHotspot(db.Model):
    """新闻热点模型"""
    __tablename__ = 'news_hotspots'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False, comment='新闻标题')
    summary = Column(Text, comment='新闻摘要')
    content = Column(Text, comment='新闻内容（可选）')
    image_url = Column(String(500), comment='封面图片URL')
    link_url = Column(String(500), comment='链接URL（可选）')
    priority = Column(Integer, default=0, comment='显示优先级（数字越大优先级越高）')
    is_active = Column(Boolean, default=True, comment='是否活跃显示')

    # 分类和标签
    category = Column(String(50), default='general', comment='新闻分类')
    tags = Column(String(200), comment='标签（逗号分隔）')

    # 显示控制
    display_order = Column(Integer, default=0, comment='显示顺序')

    # 时间字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 索引
    __table_args__ = (
        Index('idx_news_hotspots_active_priority', 'is_active', 'priority'),
        Index('idx_news_hotspots_category', 'category'),
        Index('idx_news_hotspots_created_at', 'created_at'),
    )

    def __repr__(self):
        return f'<NewsHotspot {self.id}: {self.title[:30]}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'image_url': self.image_url,
            'link_url': self.link_url,
            'priority': self.priority,
            'is_active': self.is_active,
            'category': self.category,
            'tags': self.tags.split(',') if self.tags else [],
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_active_hotspots(cls, limit=5):
        """获取活跃的热点新闻（按优先级和创建时间排序）"""
        return cls.query.filter_by(is_active=True).order_by(
            cls.priority.desc(),
            cls.created_at.desc()
        ).limit(limit).all()

    @classmethod
    def get_by_category(cls, category, limit=10):
        """按分类获取热点新闻"""
        return cls.query.filter_by(
            category=category,
            is_active=True
        ).order_by(
            cls.priority.desc(),
            cls.created_at.desc()
        ).limit(limit).all()