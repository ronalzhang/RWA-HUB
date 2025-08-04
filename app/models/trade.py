import enum
from datetime import datetime, timezone, timedelta
from app.extensions import db
from sqlalchemy.orm import validates
from sqlalchemy import event
from app.utils.validation_utils import ValidationUtils, ValidationError

class TradeType(enum.Enum):
    BUY = 'buy'    # 购买
    SELL = 'sell'  # 出售

# 添加交易状态枚举（任务3.3优化后的状态枚举）
class TradeStatus(enum.Enum):
    PENDING = 'pending'                    # 待处理
    PENDING_PAYMENT = 'pending_payment'    # 等待支付
    PENDING_CONFIRMATION = 'pending_confirmation'  # 等待链上确认
    PROCESSING = 'processing'              # 处理中
    COMPLETED = 'completed'                # 已完成
    FAILED = 'failed'                      # 失败
    CANCELLED = 'cancelled'                # 已取消
    EXPIRED = 'expired'                    # 已过期

class Trade(db.Model):
    """交易记录模型"""
    __tablename__ = 'trades'
    __table_args__ = (
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)  # 改为可空，支持无资产交易如平台费
    type = db.Column(db.String(10), nullable=False)  # buy 或 sell
    amount = db.Column(db.Integer, nullable=False)  # 交易数量
    price = db.Column(db.Float, nullable=False)  # 交易价格
    total = db.Column(db.Float, nullable=True)  # 交易总额
    token_amount = db.Column(db.Float, nullable=True)  # 购买的代币数量
    fee = db.Column(db.Float, nullable=True)  # 交易手续费
    fee_rate = db.Column(db.Float, nullable=True)  # 手续费率
    trader_address = db.Column(db.String(64), nullable=False)  # 交易者钱包地址，支持Solana长度
    tx_hash = db.Column(db.String(100))  # 交易哈希，支持各种区块链
    status = db.Column(db.String(20), default=TradeStatus.PENDING.value)  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))
    gas_used = db.Column(db.Numeric, nullable=True)  # 交易使用的gas量
    is_self_trade = db.Column(db.Boolean, nullable=False, default=False)  # 是否是自交易(和自己交易)
    payment_details = db.Column(db.Text)  # 支付详情，JSON格式
    
    # 任务3.3新增字段：优化交易状态管理
    error_message = db.Column(db.Text, nullable=True)  # 错误消息
    confirmation_count = db.Column(db.Integer, default=0)  # 区块链确认数
    estimated_completion_time = db.Column(db.DateTime, nullable=True)  # 预估完成时间
    status_updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))  # 状态更新时间
    retry_count = db.Column(db.Integer, default=0)  # 重试次数
    blockchain_network = db.Column(db.String(20), default='solana')  # 区块链网络

    # 添加与 Asset 的关系
    asset = db.relationship("Asset", back_populates="trades")

    @validates('type')
    def validate_type(self, key, value):
        if value not in [t.value for t in TradeType]:
            raise ValueError('Invalid trade type')
        return value

    @validates('amount')
    def validate_amount(self, key, value):
        if value <= 0:
            raise ValueError('Trade amount must be greater than 0')
        return value

    @validates('price')
    def validate_price(self, key, value):
        # 对于平台费交易(asset_id为None的情况)，允许price为0
        if hasattr(self, 'asset_id') and self.asset_id is None:
            return value
            
        if value <= 0:
            raise ValueError('Trade price must be greater than 0')
        return value

    @validates('trader_address')
    def validate_trader_address(self, key, address):
        """统一的地址验证和标准化"""
        if not address:
            return address
        
        if not ValidationUtils.validate_wallet_address(address):
            raise ValidationError('无效的交易者地址格式', field='trader_address')
        
        return ValidationUtils.normalize_address(address)

    def to_dict(self):
        """转换为字典格式 - 使用统一的数据转换器"""
        from app.utils.data_converters import TradeDataConverter
        return TradeDataConverter.to_api_format(self)
    
    def get_status_text(self):
        """获取状态文本描述（任务3.3状态文本）"""
        status_map = {
            TradeStatus.PENDING.value: '待处理',
            TradeStatus.PENDING_PAYMENT.value: '等待支付',
            TradeStatus.PENDING_CONFIRMATION.value: '等待确认',
            TradeStatus.PROCESSING.value: '处理中',
            TradeStatus.COMPLETED.value: '已完成',
            TradeStatus.FAILED.value: '失败',
            TradeStatus.CANCELLED.value: '已取消',
            'expired': '已过期'
        }
        return status_map.get(self.status, f'未知状态({self.status})')
    
    def can_transition_to(self, new_status: str) -> bool:
        """检查是否可以转换到新状态（任务3.3状态转换验证）"""
        valid_transitions = {
            TradeStatus.PENDING.value: [
                TradeStatus.PENDING_PAYMENT.value,
                TradeStatus.FAILED.value,
                TradeStatus.CANCELLED.value
            ],
            TradeStatus.PENDING_PAYMENT.value: [
                TradeStatus.PENDING_CONFIRMATION.value,
                TradeStatus.PROCESSING.value,
                TradeStatus.FAILED.value,
                TradeStatus.CANCELLED.value,
                'expired'
            ],
            TradeStatus.PENDING_CONFIRMATION.value: [
                TradeStatus.COMPLETED.value,
                TradeStatus.FAILED.value,
                'expired'
            ],
            TradeStatus.PROCESSING.value: [
                TradeStatus.COMPLETED.value,
                TradeStatus.FAILED.value
            ],
            TradeStatus.COMPLETED.value: [],
            TradeStatus.FAILED.value: [
                TradeStatus.PENDING.value  # 允许重试
            ],
            TradeStatus.CANCELLED.value: [],
            'expired': [
                TradeStatus.PENDING.value  # 允许重新开始
            ]
        }
        
        allowed_transitions = valid_transitions.get(self.status, [])
        return new_status in allowed_transitions
    
    def update_status(self, new_status: str, context: dict = None):
        """更新交易状态（任务3.3状态更新方法）"""
        if not self.can_transition_to(new_status):
            raise ValueError(f'Invalid status transition from {self.status} to {new_status}')
        
        old_status = self.status
        self.status = new_status
        self.status_updated_at = datetime.now(timezone(timedelta(hours=8)))
        
        # 更新相关字段
        if context:
            if 'error_message' in context:
                self.error_message = context['error_message']
            if 'tx_hash' in context:
                self.tx_hash = context['tx_hash']
            if 'confirmation_count' in context:
                self.confirmation_count = context['confirmation_count']
            if 'estimated_completion_time' in context:
                self.estimated_completion_time = context['estimated_completion_time']
        
        # 记录状态变更历史
        try:
            import json
            status_change = {
                'from_status': old_status,
                'to_status': new_status,
                'changed_at': self.status_updated_at.isoformat(),
                'context': context or {}
            }
            
            # 更新payment_details中的状态历史
            if self.payment_details:
                payment_data = json.loads(self.payment_details)
            else:
                payment_data = {}
            
            if 'status_history' not in payment_data:
                payment_data['status_history'] = []
            
            payment_data['status_history'].append(status_change)
            payment_data['current_status'] = new_status
            payment_data['last_updated'] = self.status_updated_at.isoformat()
            
            self.payment_details = json.dumps(payment_data)
            
        except Exception as e:
            # 状态历史记录失败不影响状态更新
            pass
    
    def is_active(self) -> bool:
        """检查交易是否处于活跃状态（任务3.3活跃状态检查）"""
        active_statuses = [
            TradeStatus.PENDING.value,
            TradeStatus.PENDING_PAYMENT.value,
            TradeStatus.PENDING_CONFIRMATION.value,
            TradeStatus.PROCESSING.value
        ]
        return self.status in active_statuses
    
    def is_final(self) -> bool:
        """检查交易是否处于最终状态（任务3.3最终状态检查）"""
        final_statuses = [
            TradeStatus.COMPLETED.value,
            TradeStatus.FAILED.value,
            TradeStatus.CANCELLED.value,
            'expired'
        ]
        return self.status in final_statuses 