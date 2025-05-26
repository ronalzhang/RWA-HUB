from app.extensions import db
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# 导入基本模型
from .user import User, UserRole, UserStatus
from .asset import Asset, AssetType, AssetStatus, AssetStatusHistory
from .trade import Trade, TradeStatus, TradeType
from .income import PlatformIncome, IncomeType
from .dividend import Dividend, DividendRecord
from .shortlink import ShortLink
from .transaction import Transaction, TransactionType, TransactionStatus
from .holding import Holding

# 从admin.py导入管理相关模型（删除CommissionRecord）
from .admin import (
    AdminUser, SystemConfig, CommissionSetting, 
    DistributionLevel, UserReferral, AdminOperationLog,
    DashboardStats
)

# 导入新的分销模型
from .referral import UserReferral as NewUserReferral, CommissionRecord, DistributionSetting

# 兼容旧版本
from .commission import Commission

# 导入佣金系统模型
from .commission_config import CommissionConfig, UserCommissionBalance
from .commission_withdrawal import CommissionWithdrawal

# 导出所有模型
__all__ = [
    'db', 'Asset', 'AssetType', 'AssetStatus', 'AssetStatusHistory', 'DividendRecord', 'Dividend', 
    'Trade', 'TradeType', 'TradeStatus', 'User', 'UserRole', 'UserStatus', 
    'Commission', 'AdminUser', 'SystemConfig', 'CommissionSetting',
    'DistributionLevel', 'UserReferral', 'CommissionRecord', 'AdminOperationLog',
    'DashboardStats', 'ShortLink', 'Transaction', 'TransactionType', 'TransactionStatus',
    'Holding', 'CommissionConfig', 'UserCommissionBalance', 'CommissionWithdrawal'
]
