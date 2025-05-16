import enum
import json
from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import validates
from sqlalchemy import Index, CheckConstraint
import re
from flask import current_app, url_for
from urllib.parse import urlparse
from sqlalchemy.dialects.postgresql import JSON

class AssetType(enum.Enum):
    REAL_ESTATE = 10        # 不动产
    COMMERCIAL = 20         # 类不动产
    INDUSTRIAL = 30         # 工业地产
    LAND = 40               # 土地资产
    SECURITIES = 50         # 证券资产
    ART = 60                # 艺术品
    COLLECTIBLES = 70       # 收藏品
    OTHER = 99              # 其他资产

class AssetStatus(enum.Enum):
    PENDING = 1    # 待审核
    APPROVED = 2  # 已通过
    REJECTED = 3  # 已拒绝
    DELETED = 4    # 已删除
    ON_CHAIN = 2  # 已上链（与APPROVED相同值，保持兼容性）
    ACTIVE = 2     # 活跃状态（与APPROVED和ON_CHAIN相同值，保持兼容性）
    CONFIRMED = 5  # 支付已确认，准备上链
    PAYMENT_FAILED = 6  # 支付失败
    DEPLOYMENT_FAILED = 7  # 部署上链失败
    DRAFT = 3  # 草稿状态

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
    token_address = db.Column(db.String(128), unique=True)
    annual_revenue = db.Column(db.Float, nullable=False)
    _images = db.Column('images', db.Text)
    _documents = db.Column('documents', db.Text)
    status = db.Column(db.Integer, nullable=False, default=AssetStatus.PENDING.value)
    reject_reason = db.Column(db.String(200))
    owner_address = db.Column(db.String(128), nullable=False)
    creator_address = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # 软删除标记
    remaining_supply = db.Column(db.Integer)  # 剩余可售数量
    
    # 区块链相关字段
    blockchain_details = db.Column(db.Text)  # 区块链部署详情，JSON格式
    deployment_tx_hash = db.Column(db.String(100))  # 部署交易哈希
    
    # 支付相关字段
    payment_tx_hash = db.Column(db.String(255), nullable=True)  # 支付交易哈希
    payment_details = db.Column(db.Text, nullable=True)  # 支付详情（JSON字符串）
    payment_confirmed = db.Column(db.Boolean, default=False)  # 支付是否已确认
    payment_confirmed_at = db.Column(db.DateTime, nullable=True)  # 支付确认时间
    error_message = db.Column(db.Text, nullable=True)  # 错误消息
    
    # 添加审核信息
    approved_at = db.Column(db.DateTime)  # 审核通过时间
    approved_by = db.Column(db.String(64))  # 审核人地址

    # 添加关联
    trades = db.relationship("Trade", back_populates="asset", lazy=True, cascade="all, delete-orphan")
    dividend_records = db.relationship("DividendRecord", back_populates="asset", lazy=True, cascade="all, delete-orphan")
    dividends = db.relationship("Dividend", back_populates="asset", lazy=True, cascade="all, delete-orphan")

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
        CheckConstraint('status IN (1, 2, 3, 4, 5, 6, 7)', name='ck_status_valid'),  # 状态必须在有效范围内
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
        # 修改验证规则，接受 RH-XXYYYY 格式
        pattern = r'^RH-(?:10|20)\d{4}$'
        if not re.match(pattern, value):
            raise ValueError('代币符号格式无效，必须为 RH-10YYYY 或 RH-20YYYY 格式，其中 YYYY 为4位数字')
        return value

    @validates('token_address')
    def validate_token_address(self, key, value):
        if value:
            # 修改验证规则，接受更长的Solana地址
            if not (re.match(r'^0x[a-fA-F0-9]{40}$', value) or    # 以太坊地址格式
                   re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,126}$', value)):  # Solana 地址格式(最长126个字符)
                raise ValueError('无效的代币地址格式')
        return value

    @validates('owner_address')
    def validate_owner_address(self, key, value):
        # 修改验证规则，接受更长的Solana地址
        if not (re.match(r'^0x[a-fA-F0-9]{40}$', value) or    # 以太坊地址格式
               re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,126}$', value)):  # Solana 地址格式(最长126个字符)
            raise ValueError('无效的所有者地址格式')
        return value

    @validates('creator_address')
    def validate_creator_address(self, key, value):
        # 修改验证规则，接受更长的Solana地址
        if not (re.match(r'^0x[a-fA-F0-9]{40}$', value) or    # 以太坊地址格式
               re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,126}$', value)):  # Solana 地址格式(最长126个字符)
            raise ValueError('无效的创建者地址格式')
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

    @property
    def images(self):
        """获取资产图片列表"""
        try:
            if not self._images:
                return []
            
            # 尝试解析 JSON
            images = json.loads(self._images)
            if not isinstance(images, list):
                return []
            
            # 如果URL已经是完整的，直接返回
            return [img for img in images if img and isinstance(img, str)]
            
        except Exception as e:
            current_app.logger.error(f'解析图片列表失败: {str(e)}')
            return []

    @images.setter
    def images(self, value):
        """设置资产图片列表"""
        if value is None:
            self._images = '[]'
            return
        
        if isinstance(value, str):
            try:
                # 尝试解析 JSON
                json.loads(value)
                self._images = value
            except:
                # 如果不是有效的 JSON，假设是单个 URL
                self._images = json.dumps([value])
        elif isinstance(value, list):
            # 过滤空值和无效值
            valid_images = [img for img in value if img and isinstance(img, str)]
            self._images = json.dumps(valid_images)
        else:
            self._images = '[]'

    @property
    def documents(self) -> list:
        """获取文档列表"""
        try:
            if isinstance(self._documents, str):
                return json.loads(self._documents)
            return self._documents or []
        except Exception as e:
            current_app.logger.error(f'解析文档路径失败: {str(e)}')
            return []

    @documents.setter
    def documents(self, value):
        """设置文档列表"""
        if isinstance(value, str):
            self._documents = value
        else:
            self._documents = json.dumps(value) if value else None

    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)
        
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
            'price': self.token_price,  # 添加price字段，与token_price相同，保证前端兼容性
            'token_supply': self.token_supply,
            'total_supply': self.token_supply,  # 添加total_supply字段，与token_supply相同，保证前端兼容性
            'remaining_supply': self.remaining_supply,
            'token_address': self.token_address,
            'annual_revenue': self.annual_revenue,
            'status': self.status,
            'reject_reason': self.reject_reason,
            'owner_address': self.owner_address,
            'creator_address': self.creator_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'images': self.images,
            'documents': self.documents
        }

        # 根据资产类型添加特定字段
        if self.asset_type == AssetType.REAL_ESTATE.value:
            data['area'] = self.area
        elif self.asset_type == AssetType.SECURITIES.value:
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
        elif asset_type == AssetType.SECURITIES.value:
            if 'total_value' not in data:
                raise ValueError('证券资产必须提供总价值')
            if 'token_supply' not in data:
                raise ValueError('证券资产必须提供代币发行量')
                
        return Asset(**data)

    # 上链进度跟踪
    deployment_in_progress = db.Column(db.Boolean, default=False)  # 标记上链操作是否正在进行中
    deployment_started_at = db.Column(db.DateTime, nullable=True)  # 记录上链操作开始时间
