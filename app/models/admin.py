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
    __tablename__ = 'system_configs'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(50), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.config_key}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.config_key,
            'value': self.config_value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_value(cls, key, default=None):
        """获取配置值"""
        config = cls.query.filter_by(config_key=key).first()
        return config.config_value if config else default
    
    @classmethod
    def set_value(cls, key, value, description=None, updated_by=None):
        """设置配置值"""
        config = cls.query.filter_by(config_key=key).first()
        if config:
            config.config_value = value
            if description:
                config.description = description
            config.updated_at = datetime.utcnow()
        else:
            config = cls(
                config_key=key,
                config_value=value,
                description=description
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
            'operation_details': json.loads(self.operation_details) if self.operation_details else {},
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
            target_id=str(target_id) if target_id else None,
            operation_details=json.dumps(operation_details) if operation_details else None,
            ip_address=ip_address
        )
        db.session.add(log)
        db.session.commit()
        return log

# 仪表板统计
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
        return f'<DashboardStats {self.stat_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stat_date': self.stat_date.isoformat() if self.stat_date else None,
            'stat_type': self.stat_type,
            'stat_period': self.stat_period,
            'stat_value': self.stat_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def update_daily_stats(cls):
        """更新每日统计数据"""
        today = datetime.utcnow().date()
        
        # 用户统计
        user_count = User.query.count()
        cls._update_stat('user_count', 'daily', today, user_count)
        
        # 资产统计 - 只统计未删除的资产
        asset_count = Asset.query.filter(Asset.deleted_at.is_(None)).count()
        cls._update_stat('asset_count', 'daily', today, asset_count)
        
        # 交易统计
        trade_count = Trade.query.count()
        cls._update_stat('trade_count', 'daily', today, trade_count)
        
        # 交易金额统计
        trade_volume = db.session.query(func.sum(Trade.amount)).scalar() or 0
        cls._update_stat('trade_volume', 'daily', today, trade_volume)
        
        # 今日新增用户
        today_users = User.query.filter(
            func.date(User.created_at) == today
        ).count()
        cls._update_stat('new_users_today', 'daily', today, today_users)
        
        # 今日新增资产 - 只统计未删除的资产
        today_assets = Asset.query.filter(
            func.date(Asset.created_at) == today,
            Asset.deleted_at.is_(None)
        ).count()
        cls._update_stat('new_assets_today', 'daily', today, today_assets)
        
        # 今日交易
        today_trades = Trade.query.filter(
            func.date(Trade.created_at) == today
        ).count()
        cls._update_stat('trades_today', 'daily', today, today_trades)
        
        # 今日交易金额
        today_volume = db.session.query(func.sum(Trade.amount)).filter(
            func.date(Trade.created_at) == today
        ).scalar() or 0
        cls._update_stat('volume_today', 'daily', today, today_volume)
        
        db.session.commit()
    
    @classmethod
    def update_stats_from_db(cls):
        """从数据库更新统计数据"""
        try:
            # 获取当前统计数据 - 只统计未删除的资产
            stats = {
                'total_users': User.query.count(),
                'total_assets': Asset.query.filter(Asset.deleted_at.is_(None)).count(),
                'total_trades': Trade.query.count(),
                'total_volume': db.session.query(func.sum(Trade.amount)).scalar() or 0,
                'pending_assets': Asset.query.filter(Asset.status == 1, Asset.deleted_at.is_(None)).count(),
                'approved_assets': Asset.query.filter(Asset.status == 2, Asset.deleted_at.is_(None)).count(),
                'rejected_assets': Asset.query.filter(Asset.status == 3, Asset.deleted_at.is_(None)).count(),
            }
            
            # 更新今日统计
            today = datetime.utcnow().date()
            for stat_type, value in stats.items():
                cls._update_stat(stat_type, 'daily', today, value)
            
            db.session.commit()
            return stats
        except Exception as e:
            current_app.logger.error(f'更新统计数据失败: {str(e)}')
            db.session.rollback()
            return None
    
    @classmethod
    def _update_stat(cls, stat_type, period, date, value):
        """更新单个统计项"""
        stat = cls.query.filter_by(
            stat_type=stat_type,
            stat_period=period,
            stat_date=date
        ).first()
        
        if stat:
            stat.stat_value = value
            stat.updated_at = datetime.utcnow()
        else:
            stat = cls(
                stat_type=stat_type,
                stat_period=period,
                stat_date=date,
                stat_value=value
            )
            db.session.add(stat)
    
    @classmethod
    def get_trend_data(cls, stat_type, days=30):
        """获取趋势数据"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        stats = cls.query.filter(
            cls.stat_type == stat_type,
            cls.stat_period == 'daily',
            cls.stat_date >= start_date,
            cls.stat_date <= end_date
        ).order_by(cls.stat_date).all()
        
        return [
            {
                'date': stat.stat_date.isoformat(),
                'value': stat.stat_value
            }
            for stat in stats
        ]

# 数据库事件监听器
def async_task(func):
    """异步任务装饰器（简化版）"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f'异步任务执行失败: {str(e)}')
    return wrapper

# 注释掉事件监听器，避免事务冲突
# 改为在需要时手动调用统计更新

# @event.listens_for(User, 'after_insert')
# def user_created(mapper, connection, target):
#     """用户创建后更新统计"""
#     @async_task
#     def update_stats():
#         DashboardStats.update_daily_stats()
#     
#     update_stats()

# @event.listens_for(Asset, 'after_insert')
# @event.listens_for(Asset, 'after_update')
# def asset_changed(mapper, connection, target):
#     """资产变更后更新统计"""
#     @async_task
#     def update_stats():
#         DashboardStats.update_daily_stats()
#     
#     update_stats()

# @event.listens_for(Trade, 'after_insert')
# def trade_created(mapper, connection, target):
#     """交易创建后更新统计"""
#     @async_task
#     def update_stats():
#         DashboardStats.update_daily_stats()
#     
#     update_stats() 