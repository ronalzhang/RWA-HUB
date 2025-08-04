"""
业务逻辑助手
提供常用的业务处理函数，减少重复代码
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from app.extensions import db
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.trade import Trade, TradeStatus, TradeType
from app.models.user import User
from app.models.referral import UserReferral, CommissionRecord
from app.models.commission_config import UserCommissionBalance
from app.utils.validation_utils import ValidationUtils, ValidationError
from app.utils.query_helpers import AssetQueryHelper, TradeQueryHelper, UserQueryHelper

logger = logging.getLogger(__name__)


class AssetBusinessHelper:
    """资产业务逻辑助手"""
    
    @staticmethod
    def create_asset(creator_address: str, asset_data: Dict[str, Any]) -> Asset:
        """
        创建资产的统一业务逻辑
        
        Args:
            creator_address: 创建者地址
            asset_data: 资产数据
            
        Returns:
            Asset: 创建的资产对象
        """
        # 验证必填字段
        required_fields = ['name', 'asset_type', 'location', 'token_price', 'annual_revenue']
        missing_fields = [field for field in required_fields if not asset_data.get(field)]
        if missing_fields:
            raise ValidationError(f'缺少必填字段: {", ".join(missing_fields)}')
        
        # 验证创建者地址
        if not ValidationUtils.validate_wallet_address(creator_address):
            raise ValidationError('无效的创建者地址', field='creator_address')
        
        # 验证价格
        if not ValidationUtils.validate_positive_number(asset_data['token_price']):
            raise ValidationError('代币价格必须大于0', field='token_price')
        
        # 生成唯一的token_symbol
        token_symbol = AssetBusinessHelper._generate_unique_token_symbol(
            asset_data['name'], asset_data.get('asset_type', AssetType.REAL_ESTATE.value)
        )
        
        # 计算token_supply（如果是房地产且有面积）
        token_supply = asset_data.get('token_supply')
        if not token_supply and asset_data.get('asset_type') == AssetType.REAL_ESTATE.value:
            area = asset_data.get('area', 0)
            if area > 0:
                token_supply = int(area * 10000)  # 每平米10000个代币
        
        if not token_supply:
            token_supply = 1000000  # 默认发行量
        
        # 创建资产对象
        asset = Asset(
            name=asset_data['name'],
            description=asset_data.get('description', ''),
            asset_type=asset_data['asset_type'],
            location=asset_data['location'],
            area=asset_data.get('area'),
            token_symbol=token_symbol,
            token_price=Decimal(str(asset_data['token_price'])),
            token_supply=token_supply,
            remaining_supply=token_supply,
            annual_revenue=Decimal(str(asset_data['annual_revenue'])),
            total_value=asset_data.get('total_value'),
            creator_address=ValidationUtils.normalize_address(creator_address),
            owner_address=ValidationUtils.normalize_address(creator_address),
            status=AssetStatus.PENDING.value,
            images=asset_data.get('images', []),
            documents=asset_data.get('documents', [])
        )
        
        db.session.add(asset)
        db.session.commit()
        
        logger.info(f'成功创建资产: {asset.name} (ID: {asset.id}, Symbol: {token_symbol})')
        return asset
    
    @staticmethod
    def _generate_unique_token_symbol(name: str, asset_type: int, max_attempts: int = 10) -> str:
        """生成唯一的代币符号"""
        import re
        import random
        
        # 清理名称，只保留字母和数字
        clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', name)
        
        # 如果是中文，取拼音首字母或使用类型前缀
        if re.search(r'[\u4e00-\u9fff]', clean_name):
            type_prefixes = {
                AssetType.REAL_ESTATE.value: 'RE',
                AssetType.COMMERCIAL.value: 'CM',
                AssetType.INDUSTRIAL.value: 'IN',
                AssetType.LAND.value: 'LD',
                AssetType.SECURITIES.value: 'SE',
                AssetType.ART.value: 'AR',
                AssetType.COLLECTIBLES.value: 'CO'
            }
            prefix = type_prefixes.get(asset_type, 'RW')
        else:
            # 英文名称，取前几个字符
            prefix = clean_name[:4].upper() if len(clean_name) >= 4 else clean_name.upper()
        
        # 尝试生成唯一符号
        for attempt in range(max_attempts):
            if attempt == 0:
                # 第一次尝试不加随机数
                token_symbol = f'RH-{prefix}'
            else:
                # 后续尝试加随机数
                random_suffix = random.randint(100, 999)
                token_symbol = f'RH-{prefix}{random_suffix}'
            
            # 检查是否已存在
            if not AssetQueryHelper.get_asset_by_symbol(token_symbol):
                return token_symbol
        
        # 如果都失败了，使用时间戳
        timestamp = int(datetime.now().timestamp()) % 10000
        return f'RH-{prefix}{timestamp}'
    
    @staticmethod
    def approve_asset(asset_id: int, approver_address: str) -> Asset:
        """批准资产"""
        asset = Asset.query.get(asset_id)
        if not asset:
            raise ValidationError('资产不存在')
        
        if asset.status != AssetStatus.PENDING.value:
            raise ValidationError('只能批准待审核状态的资产')
        
        asset.status = AssetStatus.APPROVED.value
        asset.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f'资产已批准: {asset.name} (ID: {asset_id}) by {approver_address}')
        return asset
    
    @staticmethod
    def reject_asset(asset_id: int, reason: str, rejector_address: str) -> Asset:
        """拒绝资产"""
        asset = Asset.query.get(asset_id)
        if not asset:
            raise ValidationError('资产不存在')
        
        if asset.status != AssetStatus.PENDING.value:
            raise ValidationError('只能拒绝待审核状态的资产')
        
        asset.status = AssetStatus.REJECTED.value
        asset.reject_reason = reason
        asset.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f'资产已拒绝: {asset.name} (ID: {asset_id}) by {rejector_address}, 原因: {reason}')
        return asset
    
    @staticmethod
    def update_asset_supply(asset_id: int, amount_change: int, operation: str = 'decrease') -> Asset:
        """更新资产供应量"""
        asset = Asset.query.get(asset_id)
        if not asset:
            raise ValidationError('资产不存在')
        
        if operation == 'decrease':
            if asset.remaining_supply < amount_change:
                raise ValidationError('可售数量不足')
            asset.remaining_supply -= amount_change
        elif operation == 'increase':
            asset.remaining_supply += amount_change
        else:
            raise ValidationError('无效的操作类型')
        
        asset.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f'资产供应量已更新: {asset.name} (ID: {asset_id}), 变化: {operation} {amount_change}')
        return asset


class TradeBusinessHelper:
    """交易业务逻辑助手"""
    
    @staticmethod
    def create_trade(asset_id: int, trader_address: str, amount: int, 
                    trade_type: str = 'buy') -> Trade:
        """
        创建交易的统一业务逻辑
        
        Args:
            asset_id: 资产ID
            trader_address: 交易者地址
            amount: 交易数量
            trade_type: 交易类型 ('buy' 或 'sell')
            
        Returns:
            Trade: 创建的交易对象
        """
        # 验证参数
        if not ValidationUtils.validate_wallet_address(trader_address):
            raise ValidationError('无效的交易者地址', field='trader_address')
        
        if not ValidationUtils.validate_positive_number(amount):
            raise ValidationError('交易数量必须大于0', field='amount')
        
        # 获取资产
        asset = Asset.query.get(asset_id)
        if not asset:
            raise ValidationError('资产不存在')
        
        if asset.status != AssetStatus.ON_CHAIN.value:
            raise ValidationError('资产未上链，无法交易')
        
        # 检查供应量（买入时）
        if trade_type == 'buy' and asset.remaining_supply < amount:
            raise ValidationError('可售数量不足')
        
        # 计算交易金额
        price = asset.token_price
        total = Decimal(str(amount)) * price
        
        # 计算手续费（假设2%）
        fee_rate = Decimal('0.02')
        fee = total * fee_rate
        
        # 创建交易记录
        trade = Trade(
            asset_id=asset_id,
            trader_address=ValidationUtils.normalize_address(trader_address),
            type=trade_type,
            amount=amount,
            price=price,
            total=total,
            fee=fee,
            fee_rate=fee_rate,
            status=TradeStatus.PENDING.value,
            blockchain_network='solana'
        )
        
        db.session.add(trade)
        db.session.commit()
        
        logger.info(f'成功创建交易: 资产{asset_id}, 交易者{trader_address}, 类型{trade_type}, 数量{amount}')
        return trade
    
    @staticmethod
    def complete_trade(trade_id: int, tx_hash: str = None) -> Trade:
        """完成交易"""
        trade = Trade.query.get(trade_id)
        if not trade:
            raise ValidationError('交易不存在')
        
        if trade.status != TradeStatus.PENDING.value:
            raise ValidationError('只能完成待处理状态的交易')
        
        # 更新资产供应量
        if trade.type == 'buy':
            AssetBusinessHelper.update_asset_supply(trade.asset_id, trade.amount, 'decrease')
        elif trade.type == 'sell':
            AssetBusinessHelper.update_asset_supply(trade.asset_id, trade.amount, 'increase')
        
        # 更新交易状态
        trade.status = TradeStatus.COMPLETED.value
        trade.tx_hash = tx_hash
        trade.status_updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f'交易已完成: ID{trade_id}, 哈希{tx_hash}')
        return trade
    
    @staticmethod
    def cancel_trade(trade_id: int, reason: str = None) -> Trade:
        """取消交易"""
        trade = Trade.query.get(trade_id)
        if not trade:
            raise ValidationError('交易不存在')
        
        if trade.status not in [TradeStatus.PENDING.value, TradeStatus.PROCESSING.value]:
            raise ValidationError('只能取消待处理或处理中的交易')
        
        trade.status = TradeStatus.CANCELLED.value
        trade.error_message = reason
        trade.status_updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f'交易已取消: ID{trade_id}, 原因{reason}')
        return trade


class UserBusinessHelper:
    """用户业务逻辑助手"""
    
    @staticmethod
    def create_or_get_user(address: str, wallet_type: str = 'ethereum') -> User:
        """创建或获取用户"""
        return UserQueryHelper.get_or_create_user(address, wallet_type)
    
    @staticmethod
    def update_user_balance(user_address: str, amount: Decimal, 
                          operation: str = 'add') -> UserCommissionBalance:
        """更新用户佣金余额"""
        # 获取或创建余额记录
        balance = UserCommissionBalance.query.filter_by(user_address=user_address).first()
        if not balance:
            balance = UserCommissionBalance(
                user_address=user_address,
                total_earned=Decimal('0'),
                available_balance=Decimal('0'),
                withdrawn_amount=Decimal('0'),
                frozen_amount=Decimal('0')
            )
            db.session.add(balance)
        
        # 更新余额
        if operation == 'add':
            balance.total_earned += amount
            balance.available_balance += amount
        elif operation == 'subtract':
            if balance.available_balance < amount:
                raise ValidationError('可用余额不足')
            balance.available_balance -= amount
        elif operation == 'freeze':
            if balance.available_balance < amount:
                raise ValidationError('可用余额不足')
            balance.available_balance -= amount
            balance.frozen_amount += amount
        elif operation == 'unfreeze':
            if balance.frozen_amount < amount:
                raise ValidationError('冻结金额不足')
            balance.frozen_amount -= amount
            balance.available_balance += amount
        else:
            raise ValidationError('无效的操作类型')
        
        balance.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f'用户余额已更新: {user_address}, 操作: {operation}, 金额: {amount}')
        return balance


class ReferralBusinessHelper:
    """推荐关系业务逻辑助手"""
    
    @staticmethod
    def create_referral_relationship(user_address: str, referrer_address: str, 
                                   referral_code: str = None) -> UserReferral:
        """创建推荐关系"""
        # 验证地址
        if not ValidationUtils.validate_wallet_address(user_address):
            raise ValidationError('无效的用户地址')
        
        if not ValidationUtils.validate_wallet_address(referrer_address):
            raise ValidationError('无效的推荐人地址')
        
        if user_address == referrer_address:
            raise ValidationError('不能推荐自己')
        
        # 检查是否已有推荐关系
        existing = UserReferral.query.filter_by(user_address=user_address).first()
        if existing:
            raise ValidationError('用户已有推荐关系')
        
        # 创建推荐关系
        referral = UserReferral(
            user_address=ValidationUtils.normalize_address(user_address),
            referrer_address=ValidationUtils.normalize_address(referrer_address),
            referral_code=referral_code,
            referral_time=datetime.utcnow(),
            status='active'
        )
        
        db.session.add(referral)
        db.session.commit()
        
        logger.info(f'成功创建推荐关系: {user_address} <- {referrer_address}')
        return referral
    
    @staticmethod
    def calculate_commission(transaction_amount: Decimal, user_address: str, 
                           commission_rate: Decimal = Decimal('0.05')) -> Dict[str, Any]:
        """计算推荐佣金分配"""
        distribution = {
            'total_commission': Decimal('0'),
            'commission_records': [],
            'levels': 0
        }
        
        current_user = user_address
        level = 1
        
        # 向上追溯推荐链
        while level <= 10:  # 最多10层
            referral = UserReferral.query.filter_by(user_address=current_user).first()
            if not referral:
                break
            
            # 计算当前层级佣金
            commission_amount = transaction_amount * commission_rate
            
            # 创建佣金记录
            commission_record = {
                'level': level,
                'referrer_address': referral.referrer_address,
                'referred_address': user_address,
                'commission_amount': commission_amount,
                'commission_rate': commission_rate
            }
            
            distribution['commission_records'].append(commission_record)
            distribution['total_commission'] += commission_amount
            
            # 移动到上一级
            current_user = referral.referrer_address
            level += 1
        
        distribution['levels'] = level - 1
        return distribution
    
    @staticmethod
    def process_commission_payment(transaction_id: int, user_address: str, 
                                 transaction_amount: Decimal) -> List[CommissionRecord]:
        """处理佣金发放"""
        # 计算佣金分配
        distribution = ReferralBusinessHelper.calculate_commission(transaction_amount, user_address)
        
        # 创建佣金记录
        commission_records = []
        for record_data in distribution['commission_records']:
            commission = CommissionRecord(
                transaction_id=transaction_id,
                referrer_address=record_data['referrer_address'],
                referred_address=record_data['referred_address'],
                commission_amount=record_data['commission_amount'],
                commission_rate=record_data['commission_rate'],
                level=record_data['level'],
                status='pending',
                created_at=datetime.utcnow()
            )
            commission_records.append(commission)
            db.session.add(commission)
        
        # 更新推荐人余额
        for record_data in distribution['commission_records']:
            UserBusinessHelper.update_user_balance(
                record_data['referrer_address'],
                record_data['commission_amount'],
                'add'
            )
        
        db.session.commit()
        
        logger.info(f'佣金处理完成: 交易{transaction_id}, 用户{user_address}, 总佣金{distribution["total_commission"]}')
        return commission_records


class ValidationBusinessHelper:
    """验证业务逻辑助手"""
    
    @staticmethod
    def validate_asset_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """验证资产数据"""
        errors = {}
        
        # 验证必填字段
        required_fields = ['name', 'asset_type', 'location', 'token_price', 'annual_revenue']
        for field in required_fields:
            if not data.get(field):
                errors[field] = f'{field}是必填字段'
        
        # 验证数值字段
        if data.get('token_price') and not ValidationUtils.validate_positive_number(data['token_price']):
            errors['token_price'] = '代币价格必须大于0'
        
        if data.get('annual_revenue') and not ValidationUtils.validate_positive_number(data['annual_revenue']):
            errors['annual_revenue'] = '年收益必须大于0'
        
        if data.get('area') and not ValidationUtils.validate_positive_number(data['area']):
            errors['area'] = '面积必须大于0'
        
        # 验证字符串长度
        if data.get('name') and not ValidationUtils.validate_string_length(data['name'], 1, 100):
            errors['name'] = '资产名称长度必须在1-100字符之间'
        
        if data.get('description') and not ValidationUtils.validate_string_length(data['description'], 0, 1000):
            errors['description'] = '描述长度不能超过1000字符'
        
        return errors
    
    @staticmethod
    def validate_trade_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """验证交易数据"""
        errors = {}
        
        # 验证必填字段
        required_fields = ['asset_id', 'trader_address', 'amount']
        for field in required_fields:
            if not data.get(field):
                errors[field] = f'{field}是必填字段'
        
        # 验证地址
        if data.get('trader_address') and not ValidationUtils.validate_wallet_address(data['trader_address']):
            errors['trader_address'] = '无效的交易者地址'
        
        # 验证数量
        if data.get('amount') and not ValidationUtils.validate_positive_number(data['amount']):
            errors['amount'] = '交易数量必须大于0'
        
        return errors