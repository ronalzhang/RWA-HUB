from flask import current_app
from app.extensions import db
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, func, event
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta
import json
from enum import Enum
from app.models.user import User
from app.models.asset import Asset
from app.models.trade import Trade

# 管理员用户
class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(100), unique=True, nullable=False)
    username = Column(String(50))
    role = Column(String(20), nullable=False, default='admin')  # admin, super_admin
    permissions = Column(Text)  # JSON 存储的权限列表
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    def __repr__(self):
        return f'<AdminUser {self.wallet_address}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'wallet_address': self.wallet_address,
            'username': self.username,
            'role': self.role,
            'permissions': json.loads(self.permissions) if self.permissions else [],
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
    
    def has_permission(self, permission):
        """检查是否拥有指定权限"""
        if not self.permissions:
            return False
        perms = json.loads(self.permissions)
        return permission in perms
    
    def is_super_admin(self):
        """检查是否为超级管理员"""
        return self.role == 'super_admin'

# 系统配置
class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(80))  # 管理员钱包地址
    
    def __repr__(self):
        return f'<SystemConfig {self.key}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def get_value(cls, key, default=None):
        """获取配置值"""
        config = cls.query.filter_by(key=key).first()
        return config.value if config else default
    
    @classmethod
    def set_value(cls, key, value, description=None, updated_by=None):
        """设置配置值"""
        config = cls.query.filter_by(key=key).first()
        if config:
            config.value = value
            if description:
                config.description = description
            if updated_by:
                config.updated_by = updated_by
            config.updated_at = datetime.utcnow()
        else:
            config = cls(
                key=key,
                value=value,
                description=description,
                updated_by=updated_by
            )
            db.session.add(config)
        db.session.commit()
        return config

# 佣金设置
class CommissionSetting(db.Model):
    __tablename__ = 'commission_settings'
    
    id = Column(Integer, primary_key=True)
    asset_type_id = Column(Integer, nullable=True)  # 为空表示全局设置
    commission_rate = Column(Float, nullable=False)  # 佣金比率 (0.01 = 1%)
    min_amount = Column(Float, nullable=True)  # 最小金额，可选
    max_amount = Column(Float, nullable=True)  # 最大金额，可选
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    created_by = Column(String(80))  # 创建者钱包地址
    
    def __repr__(self):
        return f'<CommissionSetting {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'asset_type_id': self.asset_type_id,
            'commission_rate': self.commission_rate,
            'min_amount': self.min_amount,
            'max_amount': self.max_amount,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

# 分销等级
class DistributionLevel(db.Model):
    __tablename__ = 'distribution_levels'
    
    id = Column(Integer, primary_key=True)
    level = Column(Integer, unique=True, nullable=False)  # 等级值，如1,2,3
    commission_rate = Column(Float, nullable=False)  # 佣金比率 (0.01 = 1%)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DistributionLevel {self.level}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'commission_rate': self.commission_rate,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# 佣金类型枚举
class CommissionType(Enum):
    DIRECT = 'direct'       # 直接佣金
    REFERRAL = 'referral'   # 推荐佣金

# 佣金状态枚举
class CommissionStatus(Enum):
    PENDING = 'pending'     # 待发放
    PAID = 'paid'           # 已发放
    FAILED = 'failed'       # 发放失败

# 用户推荐关系模型
class UserReferral(db.Model):
    __tablename__ = 'user_referrals'
    
    id = Column(Integer, primary_key=True)
    user_address = Column(String(80), unique=True, nullable=False)  # 被推荐用户地址
    referrer_address = Column(String(80), nullable=False)  # 推荐人地址
    referral_level = Column(Integer, default=1)  # 推荐等级
    referral_code = Column(String(20))  # 推荐码
    joined_at = Column(DateTime, default=datetime.utcnow)  # 加入时间
    
    def __repr__(self):
        return f'<UserReferral {self.user_address}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_address': self.user_address,
            'referrer_address': self.referrer_address,
            'referral_level': self.referral_level,
            'referral_code': self.referral_code,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }

# 佣金记录模型
class CommissionRecord(db.Model):
    __tablename__ = 'commission_records'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey('trades.id'))
    asset_id = Column(Integer, ForeignKey('assets.id'))
    transaction_hash = Column(String(100))  # 区块链交易哈希
    recipient_address = Column(String(80), nullable=False)  # 接收佣金的钱包地址
    amount = Column(Float, nullable=False)  # 佣金金额
    token_address = Column(String(80))  # ERC20代币地址，如果适用
    commission_type = Column(String(20), nullable=False)  # direct, referral
    status = Column(String(20), default='pending')  # pending, paid, failed
    payment_time = Column(DateTime)  # 发放时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # 关系已移除，避免外键映射问题
    
    def __repr__(self):
        return f'<CommissionRecord {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'asset_id': self.asset_id,
            'transaction_hash': self.transaction_hash,
            'recipient_address': self.recipient_address,
            'amount': self.amount,
            'token_address': self.token_address,
            'commission_type': self.commission_type,
            'status': self.status,
            'payment_time': self.payment_time.isoformat() if self.payment_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# 管理员操作日志
class AdminOperationLog(db.Model):
    __tablename__ = 'admin_operation_logs'
    
    id = Column(Integer, primary_key=True)
    admin_address = Column(String(80), nullable=False)  # 管理员钱包地址
    operation_type = Column(String(50), nullable=False)  # 操作类型
    target_table = Column(String(50))  # 目标表名
    target_id = Column(String(50))  # 目标记录ID
    operation_details = Column(Text)  # 操作详情，JSON格式
    ip_address = Column(String(50))  # IP地址
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AdminOperationLog {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'admin_address': self.admin_address,
            'operation_type': self.operation_type,
            'target_table': self.target_table,
            'target_id': self.target_id,
            'operation_details': json.loads(self.operation_details) if isinstance(self.operation_details, str) else self.operation_details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def log_operation(cls, admin_address, operation_type, target_table=None, target_id=None, operation_details=None, ip_address=None):
        """记录管理员操作"""
        log = cls(
            admin_address=admin_address,
            operation_type=operation_type,
            target_table=target_table,
            target_id=target_id,
            operation_details=json.dumps(operation_details) if operation_details else None,
            ip_address=ip_address
        )
        db.session.add(log)
        db.session.commit()
        return log

# 仪表盘统计数据
class DashboardStats(db.Model):
    __tablename__ = 'dashboard_stats'
    
    id = Column(Integer, primary_key=True)
    stat_date = Column(DateTime, nullable=False)  # 统计日期
    stat_type = Column(String(50), nullable=False)  # 统计类型，如user_count, trade_volume
    stat_period = Column(String(20), nullable=False)  # 统计周期，如daily, weekly, monthly
    stat_value = Column(Float, default=0)  # 统计值
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DashboardStats {self.stat_type}_{self.stat_date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stat_date': self.stat_date.strftime('%Y-%m-%d') if self.stat_date else None,
            'stat_type': self.stat_type,
            'stat_period': self.stat_period,
            'stat_value': self.stat_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def update_daily_stats(cls):
        """更新每日统计数据"""
        from app.models.user import User
        from app.models.asset import Asset
        from app.models.trade import Trade
        
        today = datetime.utcnow().date()
        
        # 更新用户统计
        user_count = User.query.count()
        new_users = User.query.filter(func.date(User.created_at) == today).count()
        
        # 更新资产统计
        asset_count = Asset.query.filter(Asset.status != 0).count()
        asset_value = db.session.query(func.sum(Asset.total_value)).filter(Asset.status == 2).scalar() or 0
        
        # 更新交易统计
        trade_count = Trade.query.count()
        trade_volume = db.session.query(func.sum(Trade.total_price)).scalar() or 0
        
        # 更新或创建统计记录
        stats = [
            {'type': 'user_count', 'value': user_count},
            {'type': 'new_users', 'value': new_users},
            {'type': 'asset_count', 'value': asset_count},
            {'type': 'asset_value', 'value': float(asset_value)},
            {'type': 'trade_count', 'value': trade_count},
            {'type': 'trade_volume', 'value': float(trade_volume)},
        ]
        
        for stat in stats:
            # 查找今天的记录
            record = cls.query.filter_by(
                stat_date=today,
                stat_type=stat['type'],
                stat_period='daily'
            ).first()
            
            if record:
                # 更新记录
                record.stat_value = stat['value']
            else:
                # 创建新记录
                record = cls(
                    stat_date=today,
                    stat_type=stat['type'],
                    stat_period='daily',
                    stat_value=stat['value']
                )
                db.session.add(record)
        
        db.session.commit()
        return True
    
    @classmethod
    def update_stats_from_db(cls):
        """直接从数据库查询更新统计数据"""
        try:
            # 执行数据库查询更新统计数据
            current_app.logger.info("正在从数据库更新统计数据...")
            
            result = db.session.execute("""
                INSERT INTO dashboard_stats (stat_date, stat_type, stat_period, stat_value, created_at)
                VALUES
                (CURRENT_DATE, 'user_count', 'daily', (SELECT COUNT(*) FROM users), CURRENT_TIMESTAMP),
                (CURRENT_DATE, 'new_users', 'daily', (SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE), CURRENT_TIMESTAMP),
                (CURRENT_DATE, 'asset_count', 'daily', (SELECT COUNT(*) FROM assets WHERE status != 0), CURRENT_TIMESTAMP),
                (CURRENT_DATE, 'asset_value', 'daily', COALESCE((SELECT SUM(total_value) FROM assets WHERE status = 2), 0), CURRENT_TIMESTAMP),
                (CURRENT_DATE, 'trade_count', 'daily', (SELECT COUNT(*) FROM trades), CURRENT_TIMESTAMP),
                (CURRENT_DATE, 'trade_volume', 'daily', COALESCE((SELECT SUM(total_price) FROM trades), 0), CURRENT_TIMESTAMP)
                ON CONFLICT (stat_date, stat_type, stat_period) 
                DO UPDATE SET stat_value = EXCLUDED.stat_value, updated_at = CURRENT_TIMESTAMP
            """)
            
            db.session.commit()
            current_app.logger.info("统计数据已成功更新")
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"从数据库更新统计数据失败: {str(e)}")
            return False
    
    @classmethod
    def get_trend_data(cls, stat_type, days=30):
        """获取指定统计类型的趋势数据"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # 查询指定日期范围内的统计数据
        stats = cls.query.filter(
            cls.stat_type == stat_type,
            cls.stat_period == 'daily',
            cls.stat_date >= start_date,
            cls.stat_date <= end_date
        ).order_by(cls.stat_date).all()
        
        # 准备日期范围
        date_range = []
        for i in range(days + 1):
            curr_date = start_date + timedelta(days=i)
            date_range.append(curr_date)
        
        # 构建结果
        result = {
            'labels': [date.strftime('%m-%d') for date in date_range],
            'values': [0] * (days + 1)
        }
        
        # 填充数据
        date_dict = {stat.stat_date.date(): stat.stat_value for stat in stats}
        for i, date in enumerate(date_range):
            if date in date_dict:
                result['values'][i] = date_dict[date]
        
        return result

# 事件监听器 - 自动更新仪表盘统计数据
@event.listens_for(User, 'after_insert')
def user_created(mapper, connection, target):
    """用户创建后，异步更新仪表盘统计"""
    from app.utils.decorators import async_task
    
    @async_task
    def update_stats():
        DashboardStats.update_daily_stats()
    
    update_stats()

@event.listens_for(Asset, 'after_insert')
@event.listens_for(Asset, 'after_update')
def asset_changed(mapper, connection, target):
    """资产变更后，异步更新仪表盘统计"""
    from app.utils.decorators import async_task
    
    @async_task
    def update_stats():
        DashboardStats.update_daily_stats()
    
    update_stats()

@event.listens_for(Trade, 'after_insert')
def trade_created(mapper, connection, target):
    """交易创建后，异步更新仪表盘统计"""
    from app.utils.decorators import async_task
    
    @async_task
    def update_stats():
        DashboardStats.update_daily_stats()
    
    update_stats() 