from enum import IntEnum
from datetime import datetime
from app import db
from sqlalchemy.orm import validates
import json
import re

class AssetType(IntEnum):
    """资产类型枚举"""
    REAL_ESTATE = 10  # 不动产
    SEMI_REAL_ESTATE = 20  # 类不动产

class AssetStatus(IntEnum):
    """资产状态枚举"""
    PENDING = 1  # 待审核
    APPROVED = 2  # 已审核
    REJECTED = 3  # 已拒绝
    DELETED = 4  # 已删除

class Asset(db.Model):
    """资产模型"""
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    asset_type = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    area = db.Column(db.Float)  # 仅不动产需要
    total_value = db.Column(db.Float, nullable=False)
    token_price = db.Column(db.Float, nullable=False)
    token_supply = db.Column(db.Integer)
    token_symbol = db.Column(db.String(20))
    token_address = db.Column(db.String(42))  # 上链后的合约地址
    annual_revenue = db.Column(db.Float, nullable=False)
    images = db.Column(db.Text)  # JSON格式存储图片URL列表
    documents = db.Column(db.Text)  # JSON格式存储文档URL列表
    status = db.Column(db.Integer, nullable=False, default=AssetStatus.PENDING.value)
    reject_reason = db.Column(db.String(200))
    owner_address = db.Column(db.String(42), nullable=False)
    creator_address = db.Column(db.String(42), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.String(42))

    # 添加关联
    dividend_records = db.relationship('DividendRecord', backref='asset', lazy=True, cascade='all, delete-orphan')
    trades = db.relationship('Trade', backref='asset', lazy=True)

    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)
        
        # 处理图片和文档路径
        if isinstance(self.images, list):
            self.images = json.dumps(self.images)
        if isinstance(self.documents, list):
            self.documents = json.dumps(self.documents)
            
        # 如果是不动产，根据面积计算代币发行量
        if self.asset_type == AssetType.REAL_ESTATE.value and self.area:
            self.token_supply = int(self.area * 10000)  # 每平方米10000个代币

    @property
    def image_list(self):
        """获取图片URL列表"""
        if not self.images:
            return []
        try:
            return json.loads(self.images)
        except:
            return []

    @property
    def document_list(self):
        """获取文档URL列表"""
        if not self.documents:
            return []
        try:
            return json.loads(self.documents)
        except:
            return []

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'asset_type': self.asset_type,
            'location': self.location,
            'area': self.area,
            'total_value': self.total_value,
            'token_price': self.token_price,
            'token_supply': self.token_supply,
            'token_symbol': self.token_symbol,
            'token_address': self.token_address,
            'annual_revenue': self.annual_revenue,
            'images': self.image_list,
            'documents': self.document_list,
            'status': self.status,
            'reject_reason': self.reject_reason,
            'owner_address': self.owner_address,
            'creator_address': self.creator_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @validates('name')
    def validate_name(self, key, value):
        """验证资产名称"""
        if not value:
            raise ValueError('资产名称不能为空')
        if len(value) < 2 or len(value) > 100:
            raise ValueError('资产名称长度必须在2-100个字符之间')
        return value

    @validates('description')
    def validate_description(self, key, value):
        """验证资产描述"""
        if value and (len(value) < 10 or len(value) > 1000):
            raise ValueError('资产描述长度必须在10-1000个字符之间')
        return value

    @validates('location')
    def validate_location(self, key, value):
        """验证资产位置"""
        if not value:
            raise ValueError('资产位置不能为空')
        if len(value) < 5 or len(value) > 200:
            raise ValueError('资产位置长度必须在5-200个字符之间')
        return value

    @validates('area')
    def validate_area(self, key, value):
        """验证建筑面积"""
        if value is not None:
            if value <= 0:
                raise ValueError('建筑面积必须大于0')
            if value > 1000000:
                raise ValueError('建筑面积不能超过1,000,000平方米')
        return value

    @validates('total_value')
    def validate_total_value(self, key, value):
        """验证总价值"""
        if not value or value <= 0:
            raise ValueError('总价值必须大于0')
        if value > 1000000000000:  # 1万亿
            raise ValueError('总价值不能超过1万亿')
        return value

    @validates('token_price')
    def validate_token_price(self, key, value):
        """验证代币价格"""
        if not value or value <= 0:
            raise ValueError('代币价格必须大于0')
        return value

    @validates('token_supply')
    def validate_token_supply(self, key, value):
        """验证代币发行量"""
        if value is not None and value <= 0:
            raise ValueError('代币发行量必须大于0')
        return value

    @validates('annual_revenue')
    def validate_annual_revenue(self, key, value):
        """验证年收益"""
        if not value or value <= 0:
            raise ValueError('年收益必须大于0')
        if hasattr(self, 'total_value') and self.total_value and value > self.total_value:
            raise ValueError('年收益不能超过总价值')
        return value

    @validates('owner_address')
    def validate_owner_address(self, key, value):
        """验证所有者地址"""
        if not value:
            raise ValueError('所有者地址不能为空')
        if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
            raise ValueError('无效的所有者地址格式')
        return value.lower()

    @validates('creator_address')
    def validate_creator_address(self, key, value):
        """验证创建者地址"""
        if not value:
            raise ValueError('创建者地址不能为空')
        if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
            raise ValueError('无效的创建者地址格式')
        return value.lower()

    @validates('token_address')
    def validate_token_address(self, key, value):
        """验证代币合约地址"""
        if value and not re.match(r'^0x[a-fA-F0-9]{40}$', value):
            raise ValueError('无效的代币合约地址格式')
        return value.lower() if value else None
