from app.extensions import db
from datetime import datetime
from sqlalchemy import Index, UniqueConstraint

class Holding(db.Model):
    """用户资产持有记录"""
    __tablename__ = 'holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    
    # 持有数量信息
    quantity = db.Column(db.Float, nullable=False, default=0)
    available_quantity = db.Column(db.Float, nullable=False, default=0)  # 可用的数量（未锁定）
    staked_quantity = db.Column(db.Float, nullable=False, default=0)     # 质押的数量
    
    # 购买信息
    purchase_price = db.Column(db.Float, nullable=True)  # 购买单价
    purchase_amount = db.Column(db.Float, nullable=True)  # 购买总金额
    
    # 上链信息
    token_address = db.Column(db.String(100), nullable=True)
    blockchain = db.Column(db.String(20), default='solana')
    is_on_chain = db.Column(db.Boolean, default=False)
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 唯一约束，确保一个用户对一个资产只有一条记录
    __table_args__ = (
        UniqueConstraint('user_id', 'asset_id', name='uix_user_asset'),
        Index('idx_user_holdings', 'user_id'),
        Index('idx_asset_holders', 'asset_id'),
        Index('idx_active_holdings', 'user_id', 'quantity'),
    )
    
    def __repr__(self):
        return f"<Holding: User {self.user_id} - Asset {self.asset_id} - Qty {self.quantity}>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'quantity': self.quantity,
            'available_quantity': self.available_quantity,
            'staked_quantity': self.staked_quantity,
            'purchase_price': self.purchase_price,
            'purchase_amount': self.purchase_amount,
            'token_address': self.token_address,
            'blockchain': self.blockchain,
            'is_on_chain': self.is_on_chain,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 