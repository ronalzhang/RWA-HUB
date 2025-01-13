from enum import IntEnum
from datetime import datetime, UTC
from typing import List, Optional
from app import db
import json
import enum

class AssetType(enum.Enum):
    """资产类型枚举"""
    REAL_ESTATE = 'REAL_ESTATE'  # 不动产
    SEMI_REAL_ESTATE = 'SEMI_REAL_ESTATE'  # 类不动产

class AssetStatus(enum.Enum):
    """资产状态枚举"""
    PENDING = 'PENDING'  # 待审核
    APPROVED = 'APPROVED'  # 已通过
    REJECTED = 'REJECTED'  # 已拒绝
    DELETED = 'DELETED'  # 已删除

class Asset(db.Model):
    """资产模型"""
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    asset_type = db.Column(db.Enum(AssetType), nullable=False)
    token_code = db.Column(db.String(10), nullable=False)
    token_symbol = db.Column(db.String(20), nullable=False)
    token_price = db.Column(db.Float, nullable=False)
    token_supply = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(200), nullable=False)
    area = db.Column(db.Float, nullable=True)
    total_value = db.Column(db.Float, nullable=True)
    annual_revenue = db.Column(db.Float, nullable=False)
    images = db.Column(db.Text, nullable=True)
    documents = db.Column(db.Text, nullable=True)
    owner_address = db.Column(db.String(42), nullable=False)
    token_address = db.Column(db.String(42), nullable=True)  # 代币合约地址
    status = db.Column(db.Enum(AssetStatus), nullable=False, default=AssetStatus.PENDING)
    reject_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def calculated_total_value(self):
        """计算资产总价值"""
        if self.asset_type == AssetType.REAL_ESTATE:
            # 不动产：总价值 = 面积 × 代币价格
            return self.area * self.token_price if self.area and self.token_price else 0
        else:
            # 类不动产：使用设定的总价值
            return self.total_value if self.total_value else 0

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'asset_type': self.asset_type.value,
            'token_code': self.token_code,
            'token_symbol': self.token_symbol,
            'token_price': self.token_price,
            'token_supply': self.token_supply,
            'location': self.location,
            'area': self.area,
            'total_value': self.total_value,
            'annual_revenue': self.annual_revenue,
            'images': json.loads(self.images) if self.images else [],
            'documents': json.loads(self.documents) if self.documents else [],
            'owner_address': self.owner_address,
            'status': self.status.value,
            'reject_reason': self.reject_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Asset":
        """从字典创建资产"""
        return cls(
            name=data["name"],
            description=data.get("description"),
            asset_type=AssetType(data["asset_type"]),
            token_code=data.get("token_code"),
            token_symbol=data.get("token_symbol"),
            area=data.get("area"),
            total_value=data.get("total_value"),
            token_price=data["token_price"],
            token_supply=data.get("token_supply"),
            location=data["location"],
            owner_address=data["owner_address"],
            images=data.get("images", []),
            documents=data.get("documents", []),
            annual_revenue=data.get("annual_revenue", 0)
        )
