import enum
import json
from datetime import datetime
from .. import db
from sqlalchemy.orm import validates
from sqlalchemy import Index, CheckConstraint
import re

class AssetType(enum.Enum):
    REAL_ESTATE = 10        # 不动产
    SEMI_REAL_ESTATE = 20  # 类不动产

class AssetStatus(enum.Enum):
    PENDING = 1    # 待审核
    APPROVED = 2  # 已通过
    REJECTED = 3  # 已拒绝
    DELETED = 4    # 已删除

class Asset(db.Model):
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    asset_type = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    area = db.Column(db.Float)
    total_value = db.Column(db.Float)
    token_symbol = db.Column(db.String(20), nullable=False, unique=True)
    token_price = db.Column(db.Float, nullable=False)
    token_supply = db.Column(db.Integer)
    token_address = db.Column(db.String(42), unique=True)
    annual_revenue = db.Column(db.Float, nullable=False)
    images = db.Column(db.Text)
    documents = db.Column(db.Text)
    status = db.Column(db.Integer, nullable=False, default=AssetStatus.PENDING.value)
    reject_reason = db.Column(db.String(200))
    owner_address = db.Column(db.String(42), nullable=False)
    creator_address = db.Column(db.String(42), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.String(42))

    # 添加关联
    dividend_records = db.relationship('app.models.dividend.DividendRecord', backref='asset', lazy=True, cascade='all, delete-orphan')
    trades = db.relationship('app.models.trade.Trade', backref='asset', lazy=True)

    # 添加索引
    __table_args__ = (
        Index('ix_assets_name', 'name'),  # 名称索引
        Index('ix_assets_location', 'location'),  # 位置索引
        Index('ix_assets_asset_type', 'asset_type'),  # 资产类型索引
        Index('ix_assets_status', 'status'),  # 状态索引
        Index('ix_assets_created_at', 'created_at'),  # 创建时间索引
        CheckConstraint('token_price > 0', name='ck_token_price_positive'),  # 代币价格必须大于0
        CheckConstraint('token_supply > 0', name='ck_token_supply_positive'),  # 代币供应量必须大于0
        CheckConstraint('annual_revenue > 0', name='ck_annual_revenue_positive'),  # 年收益必须大于0
        CheckConstraint('area > 0', name='ck_area_positive'),  # 面积必须大于0
        CheckConstraint('total_value > 0', name='ck_total_value_positive'),  # 总价值必须大于0
        CheckConstraint('status IN (1, 2, 3, 4)', name='ck_status_valid'),  # 状态必须在有效范围内
    )

    @validates('asset_type')
    def validate_asset_type(self, key, value):
        if value not in [t.value for t in AssetType]:
            raise ValueError('Invalid asset type')
        return value

    @validates('status')
    def validate_status(self, key, value):
        if value not in [s.value for s in AssetStatus]:
            raise ValueError('Invalid status')
        return value

    @validates('token_symbol')
    def validate_token_symbol(self, key, value):
        pattern = r'^RH-(?:10|20)\d{4}$'
        if not re.match(pattern, value):
            raise ValueError('Invalid token symbol format. Must be RH-XXYYYY where XX is 10 or 20 and YYYY is 4 digits')
        return value

    @validates('token_address')
    def validate_token_address(self, key, value):
        if value:
            if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
                raise ValueError('Invalid token address format')
        return value

    @validates('owner_address')
    def validate_owner_address(self, key, value):
        if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
            raise ValueError('Invalid owner address format')
        return value

    @validates('creator_address')
    def validate_creator_address(self, key, value):
        if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
            raise ValueError('Invalid creator address format')
        return value

    @validates('token_price')
    def validate_token_price(self, key, value):
        if value <= 0:
            raise ValueError('Token price must be greater than 0')
        return value

    @validates('token_supply')
    def validate_token_supply(self, key, value):
        if value <= 0:
            raise ValueError('Token supply must be greater than 0')
        return value

    @validates('area')
    def validate_area(self, key, value):
        if value is not None and value <= 0:
            raise ValueError('Area must be greater than 0')
        return value

    @validates('total_value')
    def validate_total_value(self, key, value):
        if value is not None and value <= 0:
            raise ValueError('Total value must be greater than 0')
        return value

    @validates('annual_revenue')
    def validate_annual_revenue(self, key, value):
        if value <= 0:
            raise ValueError('Annual revenue must be greater than 0')
        return value

    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)
        
        # 处理图片和文档路径
        if isinstance(self.images, list):
            self.images = json.dumps(self.images)
        if isinstance(self.documents, list):
            self.documents = json.dumps(self.documents)
            
        # 如果是不动产，根据面积计算代币发行量
        if self.asset_type == AssetType.REAL_ESTATE.value and self.area:
            self.token_supply = int(self.area * 10000)

    def to_dict(self):
        """转换为字典格式"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'asset_type': self.asset_type,
            'location': self.location,
            'token_symbol': self.token_symbol,
            'token_price': self.token_price,
            'token_supply': self.token_supply,
            'token_address': self.token_address,
            'annual_revenue': self.annual_revenue,
            'status': self.status,
            'reject_reason': self.reject_reason,
            'owner_address': self.owner_address,
            'creator_address': self.creator_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'deleted_at': self.deleted_at.strftime('%Y-%m-%d %H:%M:%S') if self.deleted_at else None,
            'deleted_by': self.deleted_by
        }

        # 处理图片和文档路径
        try:
            data['images'] = json.loads(self.images) if self.images else []
        except:
            data['images'] = []
            
        try:
            data['documents'] = json.loads(self.documents) if self.documents else []
        except:
            data['documents'] = []

        # 根据资产类型添加特定字段
        if self.asset_type == AssetType.REAL_ESTATE.value:
            data['area'] = self.area
        elif self.asset_type == AssetType.SEMI_REAL_ESTATE.value:
            data['total_value'] = self.total_value

        return data

    @staticmethod
    def from_dict(data):
        """从字典创建实例"""
        # 验证必填字段
        required_fields = ['name', 'asset_type', 'location', 'token_price', 'annual_revenue', 'owner_address']
        for field in required_fields:
            if field not in data:
                raise ValueError(f'缺少必填字段: {field}')
        
        # 验证资产类型特定字段
        asset_type = data['asset_type']
        if asset_type == AssetType.REAL_ESTATE.value:
            if 'area' not in data:
                raise ValueError('不动产类型必须提供面积')
        else:
            if 'total_value' not in data:
                raise ValueError('类不动产必须提供总价值')
            if 'token_supply' not in data:
                raise ValueError('类不动产必须提供代币发行量')
                
        return Asset(**data)
