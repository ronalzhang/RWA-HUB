"""
平台收入记录模型
"""
import enum
from datetime import datetime
from enum import Enum, auto
import json
from sqlalchemy import Index

from app.extensions import db

class IncomeType(enum.Enum):
    """收入类型"""
    ASSET_ONCHAIN = 1  # 资产上链费用
    TRANSACTION = 2    # 交易手续费
    DIVIDEND = 3       # 分红手续费
    OTHER = 99         # 其他收入

class PlatformIncome(db.Model):
    """平台收入记录模型"""
    __tablename__ = 'platform_incomes'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, nullable=False)  # 收入类型
    amount = db.Column(db.Float, nullable=False)  # 收入金额
    description = db.Column(db.String(200))       # 收入描述
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'))  # 关联资产ID
    related_id = db.Column(db.Integer)  # 关联记录ID（交易或分红ID）
    tx_hash = db.Column(db.String(100))  # 交易哈希
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联的资产
    asset = db.relationship('Asset', foreign_keys=[asset_id], backref=db.backref('incomes', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        super(PlatformIncome, self).__init__(**kwargs)
    
    def to_dict(self):
        """转为字典"""
        # 获取收入类型的中文名称
        type_names = {
            IncomeType.ASSET_ONCHAIN.value: '上链服务费',
            IncomeType.TRANSACTION.value: '交易佣金',
            IncomeType.DIVIDEND.value: '分红手续费',
            IncomeType.OTHER.value: '其他收入'
        }
        
        # 尝试从关联资产获取名称和symbol
        asset_name = ""
        asset_symbol = ""
        if hasattr(self, 'asset') and self.asset:
            asset_name = self.asset.name
            asset_symbol = self.asset.token_symbol
            
        return {
            'id': self.id,
            'type': self.type,
            'type_name': type_names.get(self.type, '未知类型'),
            'type_text': IncomeType(self.type).name if self.type in [t.value for t in IncomeType] else 'UNKNOWN',
            'amount': self.amount,
            'description': self.description,
            'asset_id': self.asset_id,
            'asset_name': asset_name,
            'asset_symbol': asset_symbol,
            'related_id': self.related_id,
            'tx_hash': self.tx_hash,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'timestamp': int(self.created_at.timestamp() * 1000) if self.created_at else None
        }
        
# 记录平台收入的辅助函数
def record_income(income_type, amount, description=None, asset_id=None, related_id=None, tx_hash=None):
    """记录平台收入"""
    try:
        income = PlatformIncome(
            type=income_type.value,
            amount=amount,
            description=description,
            asset_id=asset_id,
            related_id=related_id,
            tx_hash=tx_hash
        )
        db.session.add(income)
        db.session.commit()
        return income
    except Exception as e:
        db.session.rollback()
        raise e 