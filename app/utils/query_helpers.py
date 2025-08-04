"""
统一查询助手
提供常用的数据库查询方法，减少重复代码
"""

from typing import Optional, List, Dict, Any, Union
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Query
from app.extensions import db
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade, TradeStatus
from app.models.user import User
from app.models.referral import UserReferral
from app.models.commission import CommissionRecord
import logging

logger = logging.getLogger(__name__)


class AssetQueryHelper:
    """资产查询助手"""
    
    @staticmethod
    def get_active_assets_query() -> Query:
        """获取活跃资产的基础查询"""
        return Asset.query.filter(
            Asset.status == AssetStatus.ON_CHAIN.value,
            Asset.deleted_at.is_(None)
        )
    
    @staticmethod
    def get_all_assets_query(include_deleted: bool = False) -> Query:
        """获取所有资产的基础查询"""
        query = Asset.query
        if not include_deleted:
            query = query.filter(Asset.deleted_at.is_(None))
        return query
    
    @staticmethod
    def get_pending_assets_query() -> Query:
        """获取待审核资产的查询"""
        return Asset.query.filter(
            Asset.status == AssetStatus.PENDING.value,
            Asset.deleted_at.is_(None)
        )
    
    @staticmethod
    def get_approved_assets_query() -> Query:
        """获取已批准资产的查询"""
        return Asset.query.filter(
            Asset.status == AssetStatus.APPROVED.value,
            Asset.deleted_at.is_(None)
        )
    
    @staticmethod
    def get_asset_by_symbol(symbol: str) -> Optional[Asset]:
        """通过符号获取资产"""
        if not symbol:
            return None
        return Asset.query.filter_by(token_symbol=symbol.strip()).first()
    
    @staticmethod
    def get_asset_by_id(asset_id: Union[int, str]) -> Optional[Asset]:
        """通过ID获取资产（支持数字ID和符号）"""
        if not asset_id:
            return None
        
        # 如果是数字，直接查询ID
        if isinstance(asset_id, int):
            return Asset.query.get(asset_id)
        
        # 如果是字符串
        if isinstance(asset_id, str):
            # 如果是RH-格式，按符号查询
            if asset_id.startswith('RH-'):
                return AssetQueryHelper.get_asset_by_symbol(asset_id)
            
            # 尝试转换为数字ID
            try:
                numeric_id = int(asset_id)
                return Asset.query.get(numeric_id)
            except ValueError:
                # 如果转换失败，尝试按符号查询
                return AssetQueryHelper.get_asset_by_symbol(asset_id)
        
        return None
    
    @staticmethod
    def get_assets_by_creator(creator_address: str, include_deleted: bool = False) -> List[Asset]:
        """获取创建者的资产列表"""
        query = Asset.query.filter_by(creator_address=creator_address)
        if not include_deleted:
            query = query.filter(Asset.deleted_at.is_(None))
        return query.all()
    
    @staticmethod
    def get_assets_by_type(asset_type: Union[int, AssetType], include_deleted: bool = False) -> List[Asset]:
        """按类型获取资产列表"""
        type_value = asset_type.value if isinstance(asset_type, AssetType) else asset_type
        query = Asset.query.filter_by(asset_type=type_value)
        if not include_deleted:
            query = query.filter(Asset.deleted_at.is_(None))
        return query.all()
    
    @staticmethod
    def search_assets(search_term: str, include_deleted: bool = False) -> Query:
        """搜索资产"""
        query = Asset.query.filter(
            or_(
                Asset.name.ilike(f'%{search_term}%'),
                Asset.description.ilike(f'%{search_term}%'),
                Asset.token_symbol.ilike(f'%{search_term}%'),
                Asset.location.ilike(f'%{search_term}%')
            )
        )
        if not include_deleted:
            query = query.filter(Asset.deleted_at.is_(None))
        return query
    
    @staticmethod
    def get_asset_statistics() -> Dict[str, Any]:
        """获取资产统计信息"""
        return {
            'total_assets': AssetQueryHelper.get_all_assets_query().count(),
            'active_assets': AssetQueryHelper.get_active_assets_query().count(),
            'pending_assets': AssetQueryHelper.get_pending_assets_query().count(),
            'approved_assets': AssetQueryHelper.get_approved_assets_query().count(),
            'rejected_assets': Asset.query.filter(
                Asset.status == AssetStatus.REJECTED.value,
                Asset.deleted_at.is_(None)
            ).count(),
            'total_value': db.session.query(func.sum(Asset.total_value)).filter(
                Asset.status == AssetStatus.ON_CHAIN.value,
                Asset.deleted_at.is_(None)
            ).scalar() or 0
        }


class TradeQueryHelper:
    """交易查询助手"""
    
    @staticmethod
    def get_completed_trades_query() -> Query:
        """获取已完成交易的查询"""
        return Trade.query.filter(Trade.status == TradeStatus.COMPLETED.value)
    
    @staticmethod
    def get_pending_trades_query() -> Query:
        """获取待处理交易的查询"""
        return Trade.query.filter(Trade.status == TradeStatus.PENDING.value)
    
    @staticmethod
    def get_trades_by_asset(asset_id: int) -> List[Trade]:
        """获取资产的交易记录"""
        return Trade.query.filter_by(asset_id=asset_id).order_by(desc(Trade.created_at)).all()
    
    @staticmethod
    def get_trades_by_trader(trader_address: str) -> List[Trade]:
        """获取交易者的交易记录"""
        return Trade.query.filter_by(trader_address=trader_address).order_by(desc(Trade.created_at)).all()
    
    @staticmethod
    def get_user_asset_holdings(trader_address: str) -> Dict[int, Dict[str, Any]]:
        """获取用户资产持有情况"""
        # 查询用户的所有已完成交易
        completed_trades = Trade.query.filter(
            Trade.trader_address == trader_address,
            Trade.status == TradeStatus.COMPLETED.value
        ).all()
        
        # 按资产ID分组计算持有量
        holdings = {}
        for trade in completed_trades:
            asset_id = trade.asset_id
            if asset_id not in holdings:
                holdings[asset_id] = {
                    'asset_id': asset_id,
                    'total_bought': 0,
                    'total_sold': 0,
                    'current_holding': 0,
                    'total_spent': 0,
                    'total_earned': 0,
                    'trades_count': 0
                }
            
            holding = holdings[asset_id]
            holding['trades_count'] += 1
            
            if trade.type == 'buy':
                holding['total_bought'] += trade.amount
                holding['total_spent'] += trade.total
            elif trade.type == 'sell':
                holding['total_sold'] += trade.amount
                holding['total_earned'] += trade.total
            
            holding['current_holding'] = holding['total_bought'] - holding['total_sold']
        
        # 只返回当前持有量大于0的资产
        return {k: v for k, v in holdings.items() if v['current_holding'] > 0}
    
    @staticmethod
    def get_trade_statistics() -> Dict[str, Any]:
        """获取交易统计信息"""
        return {
            'total_trades': Trade.query.count(),
            'completed_trades': TradeQueryHelper.get_completed_trades_query().count(),
            'pending_trades': TradeQueryHelper.get_pending_trades_query().count(),
            'total_volume': db.session.query(func.sum(Trade.total)).filter(
                Trade.status == TradeStatus.COMPLETED.value
            ).scalar() or 0,
            'total_fees': db.session.query(func.sum(Trade.fee)).filter(
                Trade.status == TradeStatus.COMPLETED.value
            ).scalar() or 0
        }


class UserQueryHelper:
    """用户查询助手"""
    
    @staticmethod
    def get_user_by_address(address: str, wallet_type: str = None) -> Optional[User]:
        """通过地址获取用户"""
        if not address:
            return None
        
        # 标准化地址
        from app.utils.validation_utils import ValidationUtils
        normalized_address = ValidationUtils.normalize_address(address)
        
        # 构建查询条件
        conditions = []
        
        if wallet_type == 'ethereum' or address.startswith('0x'):
            conditions.append(User.eth_address == normalized_address)
        elif wallet_type == 'solana':
            conditions.append(User.solana_address == address)  # Solana地址区分大小写
        else:
            # 同时查询两种地址类型
            conditions.extend([
                User.eth_address == normalized_address,
                User.solana_address == address
            ])
        
        return User.query.filter(or_(*conditions)).first()
    
    @staticmethod
    def get_or_create_user(address: str, wallet_type: str = 'ethereum') -> User:
        """获取或创建用户"""
        user = UserQueryHelper.get_user_by_address(address, wallet_type)
        
        if not user:
            # 创建新用户
            from app.utils.validation_utils import ValidationUtils
            normalized_address = ValidationUtils.normalize_address(address)
            
            user_data = {
                'username': f'user_{address[:8]}',
                'email': f'{address[:8]}@wallet.generated',
                'role': 'user',
                'is_distributor': True,
                'wallet_type': wallet_type
            }
            
            if wallet_type == 'ethereum' or address.startswith('0x'):
                user_data['eth_address'] = normalized_address
            else:
                user_data['solana_address'] = address
            
            user = User(**user_data)
            db.session.add(user)
            
            try:
                db.session.commit()
                logger.info(f'成功创建新用户: 地址={address}, 类型={wallet_type}')
            except Exception as e:
                db.session.rollback()
                logger.error(f'创建用户失败: {str(e)}')
                raise
        
        return user
    
    @staticmethod
    def get_user_statistics() -> Dict[str, Any]:
        """获取用户统计信息"""
        return {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(status='active').count(),
            'distributors': User.query.filter_by(is_distributor=True).count(),
            'ethereum_users': User.query.filter(User.eth_address.isnot(None)).count(),
            'solana_users': User.query.filter(User.solana_address.isnot(None)).count()
        }


class ReferralQueryHelper:
    """推荐关系查询助手"""
    
    @staticmethod
    def get_direct_referrals(referrer_address: str) -> List[UserReferral]:
        """获取直接下线"""
        return UserReferral.query.filter_by(referrer_address=referrer_address).all()
    
    @staticmethod
    def get_referrer(user_address: str) -> Optional[UserReferral]:
        """获取推荐人"""
        return UserReferral.query.filter_by(user_address=user_address).first()
    
    @staticmethod
    def get_referral_chain(user_address: str, max_levels: int = 10) -> List[str]:
        """获取推荐链（向上追溯）"""
        chain = []
        current_address = user_address
        
        for _ in range(max_levels):
            referral = ReferralQueryHelper.get_referrer(current_address)
            if not referral:
                break
            
            chain.append(referral.referrer_address)
            current_address = referral.referrer_address
            
            # 防止循环引用
            if current_address in chain[:-1]:
                break
        
        return chain
    
    @staticmethod
    def get_referral_tree_depth(referrer_address: str, visited: set = None) -> int:
        """计算推荐树深度"""
        if visited is None:
            visited = set()
        
        if referrer_address in visited:
            return 0
        
        visited.add(referrer_address)
        
        direct_referrals = ReferralQueryHelper.get_direct_referrals(referrer_address)
        if not direct_referrals:
            return 1
        
        max_depth = 0
        for referral in direct_referrals:
            depth = ReferralQueryHelper.get_referral_tree_depth(
                referral.user_address, visited.copy()
            )
            max_depth = max(max_depth, depth)
        
        return max_depth + 1
    
    @staticmethod
    def get_referral_statistics(referrer_address: str) -> Dict[str, Any]:
        """获取推荐统计信息"""
        direct_referrals = ReferralQueryHelper.get_direct_referrals(referrer_address)
        
        # 计算总佣金
        total_commission = db.session.query(func.sum(CommissionRecord.commission_amount)).filter(
            CommissionRecord.referrer_address == referrer_address
        ).scalar() or 0
        
        return {
            'direct_referrals_count': len(direct_referrals),
            'total_commission': float(total_commission),
            'tree_depth': ReferralQueryHelper.get_referral_tree_depth(referrer_address),
            'direct_referrals': [r.user_address for r in direct_referrals]
        }


class QueryBuilder:
    """通用查询构建器"""
    
    def __init__(self, model_class):
        self.model_class = model_class
        self.query = model_class.query
        self._filters = []
        self._orders = []
        self._limit_value = None
        self._offset_value = None
    
    def filter_by(self, **kwargs):
        """按字段过滤"""
        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                self._filters.append(getattr(self.model_class, key) == value)
        return self
    
    def filter(self, *conditions):
        """添加过滤条件"""
        self._filters.extend(conditions)
        return self
    
    def order_by(self, *columns):
        """添加排序"""
        self._orders.extend(columns)
        return self
    
    def limit(self, limit):
        """限制结果数量"""
        self._limit_value = limit
        return self
    
    def offset(self, offset):
        """设置偏移量"""
        self._offset_value = offset
        return self
    
    def build(self) -> Query:
        """构建查询"""
        query = self.query
        
        # 应用过滤条件
        if self._filters:
            query = query.filter(and_(*self._filters))
        
        # 应用排序
        if self._orders:
            query = query.order_by(*self._orders)
        
        # 应用限制和偏移
        if self._limit_value:
            query = query.limit(self._limit_value)
        
        if self._offset_value:
            query = query.offset(self._offset_value)
        
        return query
    
    def all(self):
        """获取所有结果"""
        return self.build().all()
    
    def first(self):
        """获取第一个结果"""
        return self.build().first()
    
    def count(self):
        """获取结果数量"""
        return self.build().count()
    
    def paginate(self, page=1, per_page=20, error_out=False):
        """分页查询"""
        return self.build().paginate(page=page, per_page=per_page, error_out=error_out)


# 便捷函数
def query_builder(model_class):
    """创建查询构建器"""
    return QueryBuilder(model_class)


def get_model_statistics(*model_classes) -> Dict[str, int]:
    """获取多个模型的统计信息"""
    stats = {}
    for model_class in model_classes:
        model_name = model_class.__name__.lower()
        stats[f'{model_name}_count'] = model_class.query.count()
    return stats


def batch_update(model_class, filters: Dict, updates: Dict) -> int:
    """批量更新"""
    query = model_class.query
    
    # 应用过滤条件
    for key, value in filters.items():
        if hasattr(model_class, key):
            query = query.filter(getattr(model_class, key) == value)
    
    # 执行更新
    count = query.update(updates)
    db.session.commit()
    
    return count


def batch_delete(model_class, filters: Dict) -> int:
    """批量删除"""
    query = model_class.query
    
    # 应用过滤条件
    for key, value in filters.items():
        if hasattr(model_class, key):
            query = query.filter(getattr(model_class, key) == value)
    
    # 执行删除
    count = query.delete()
    db.session.commit()
    
    return count