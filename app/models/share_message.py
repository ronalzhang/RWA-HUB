from datetime import datetime
from app.extensions import db

class ShareMessage(db.Model):
    """分享消息模型"""
    __tablename__ = 'share_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False, comment='分享消息内容')
    message_type = db.Column(db.String(50), nullable=False, default='share_content', comment='消息类型：share_content=分享内容，reward_plan=奖励计划')
    weight = db.Column(db.Integer, default=100, comment='权重，数值越大越容易被选中')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    @classmethod
    def get_random_message(cls, message_type='share_content'):
        """获取随机消息"""
        import random
        
        # 获取指定类型的活跃消息
        messages = cls.query.filter_by(
            message_type=message_type,
            is_active=True
        ).all()
        
        if not messages:
            # 如果没有找到指定类型的消息，返回默认消息
            if message_type == 'reward_plan':
                return "一次分享，终身收益 - 无限下级20%分成"
            else:
                return "🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。"
        
        # 根据权重随机选择
        total_weight = sum(msg.weight for msg in messages)
        if total_weight == 0:
            return random.choice(messages).content
        
        random_num = random.randint(1, total_weight)
        current_weight = 0
        
        for message in messages:
            current_weight += message.weight
            if random_num <= current_weight:
                return message.content
        
        # 兜底返回第一个消息
        return messages[0].content
    
    @classmethod
    def get_default_messages(cls):
        """获取默认的分享消息列表"""
        return [
            "📈 分享赚佣金！邀请好友投资，您可获得高达30%的推广佣金！链接由您独享，佣金终身受益，朋友越多，收益越丰厚！",
            "🤝 好东西就要和朋友分享！发送您的专属链接，让更多朋友加入这个投资社区，一起交流，共同成长，还能获得持续佣金回报！",
            "🔥 发现好机会就要分享！邀请好友一起投资这个优质资产，共同见证财富增长！您的专属链接，助力朋友也能抓住这个机会！"
        ]
    
    @classmethod
    def init_default_messages(cls):
        """初始化默认分享消息"""
        # 检查是否已有数据
        if cls.query.count() > 0:
            return
            
        # 添加默认消息
        default_messages = cls.get_default_messages()
        for content in default_messages:
            message = cls(content=content, is_active=True, weight=1)
            db.session.add(message)
            
        db.session.commit()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'content': self.content,
            'message_type': self.message_type,
            'weight': self.weight,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 