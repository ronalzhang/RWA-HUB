"""
无限层级推荐系统
实现无限层级推荐关系管理和佣金计算
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.referral import UserReferral, CommissionRecord
from app.models.commission_config import UserCommissionBalance, CommissionConfig
from app.models.trade import Trade

logger = logging.getLogger(__name__)


class UnlimitedReferralSystem:
    """无限层级推荐系统"""
    
    def __init__(self):
        self.referral_rate = Decimal('0.05')  # 5%固定上供比例
        self.platform_base_rate = Decimal('0.10')  # 10%平台基础抽成
        
    def register_referral(self, user_address: str, referrer_address: str, referral_code: str = None) -> UserReferral:
        """
        注册推荐关系
        
        Args:
            user_address: 用户钱包地址
            referrer_address: 推荐人钱包地址
            referral_code: 推荐码（可选）
            
        Returns:
            UserReferral: 创建的推荐关系记录
            
        Raises:
            ValueError: 当推荐关系无效时
        """
        # 1. 验证推荐关系的有效性
        if user_address == referrer_address:
            raise ValueError("不能推荐自己")
            
        # 2. 检查是否已有推荐关系
        existing = UserReferral.query.filter_by(user_address=user_address).first()
        if existing:
            raise ValueError("用户已有推荐关系")
        
        # 3. 检查是否会形成循环推荐
        if self._would_create_cycle(user_address, referrer_address):
            raise ValueError("推荐关系会形成循环，不允许")
        
        try:
            # 4. 创建推荐关系
            referral = UserReferral(
                user_address=user_address,
                referrer_address=referrer_address,
                referral_code=referral_code,
                referral_time=datetime.utcnow(),
                status='active'
            )
            db.session.add(referral)
            db.session.commit()
            
            logger.info(f"推荐关系创建成功: {user_address} -> {referrer_address}")
            return referral
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"创建推荐关系失败: {e}")
            raise ValueError("推荐关系创建失败，可能存在数据冲突")
    
    def _would_create_cycle(self, user_address: str, referrer_address: str, visited: set = None) -> bool:
        """
        检查是否会形成循环推荐
        
        Args:
            user_address: 用户地址
            referrer_address: 推荐人地址
            visited: 已访问的地址集合
            
        Returns:
            bool: 是否会形成循环
        """
        if visited is None:
            visited = set()
        
        if referrer_address in visited:
            return True
        
        visited.add(referrer_address)
        
        # 查找推荐人的推荐人
        parent_referral = UserReferral.query.filter_by(user_address=referrer_address).first()
        if parent_referral:
            return self._would_create_cycle(user_address, parent_referral.referrer_address, visited)
        
        return False
    
    def calculate_commission_distribution(self, transaction_amount: Decimal, user_address: str) -> Dict:
        """
        计算佣金分配 - 无限层级固定比例
        
        Args:
            transaction_amount: 交易金额
            user_address: 用户地址
            
        Returns:
            Dict: 佣金分配详情
        """
        distribution = {
            'platform_fee': Decimal('0'),
            'referral_commissions': [],
            'total_referral_amount': Decimal('0')
        }
        
        # 1. 计算平台基础抽成
        platform_base = transaction_amount * self.platform_base_rate
        distribution['platform_fee'] = platform_base
        
        # 2. 向上追溯推荐链，每层固定5%
        current_user = user_address
        level = 1
        
        while True:
            # 查找当前用户的推荐人
            referral = UserReferral.query.filter_by(
                user_address=current_user,
                status='active'
            ).first()
            
            if not referral:
                break  # 没有推荐人，结束追溯
            
            # 计算当前层级佣金
            commission_amount = transaction_amount * self.referral_rate
            
            # 记录佣金分配
            distribution['referral_commissions'].append({
                'level': level,
                'referrer_address': referral.referrer_address,
                'commission_amount': commission_amount,
                'rate': self.referral_rate,
                'user_address': current_user
            })
            
            distribution['total_referral_amount'] += commission_amount
            
            # 移动到上一级
            current_user = referral.referrer_address
            level += 1
            
            # 安全限制：防止无限循环（虽然数据结构上不应该出现）
            if level > 100:
                logger.warning(f"推荐链层级过深，用户: {user_address}")
                break
        
        # 3. 计算平台最终收益
        remaining_amount = transaction_amount - distribution['total_referral_amount'] - platform_base
        distribution['platform_fee'] += remaining_amount
        
        return distribution
    
    def process_referral_commissions(self, transaction_id: int, user_address: str, transaction_amount: Decimal) -> Dict:
        """
        处理推荐佣金发放
        
        Args:
            transaction_id: 交易ID
            user_address: 用户地址
            transaction_amount: 交易金额
            
        Returns:
            Dict: 佣金分配结果
        """
        try:
            # 1. 计算佣金分配
            distribution = self.calculate_commission_distribution(transaction_amount, user_address)
            
            # 2. 批量创建佣金记录
            commission_records = []
            for referral_info in distribution['referral_commissions']:
                commission = CommissionRecord(
                    transaction_id=transaction_id,
                    asset_id=self._get_asset_id_from_transaction(transaction_id),
                    recipient_address=referral_info['referrer_address'],
                    amount=float(referral_info['commission_amount']),
                    currency='USDC',
                    commission_type=f'referral_{referral_info["level"]}',
                    status='pending',
                    created_at=datetime.utcnow()
                )
                commission_records.append(commission)
            
            # 3. 批量插入数据库
            if commission_records:
                db.session.bulk_save_objects(commission_records)
            
            # 4. 更新用户佣金余额
            for referral_info in distribution['referral_commissions']:
                self._update_user_commission_balance(
                    referral_info['referrer_address'],
                    referral_info['commission_amount']
                )
            
            db.session.commit()
            
            logger.info(f"佣金分配完成，交易ID: {transaction_id}, 总佣金: {distribution['total_referral_amount']}")
            return distribution
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"处理推荐佣金失败: {e}")
            raise
    
    def _get_asset_id_from_transaction(self, transaction_id: int) -> Optional[int]:
        """从交易记录获取资产ID"""
        trade = Trade.query.get(transaction_id)
        return trade.asset_id if trade else None
    
    def _update_user_commission_balance(self, user_address: str, amount: Decimal):
        """
        更新用户佣金余额
        
        Args:
            user_address: 用户地址
            amount: 佣金金额
        """
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
        
        balance.total_earned += amount
        balance.available_balance += amount
        balance.last_updated = datetime.utcnow()
    
    def get_referral_statistics(self, user_address: str) -> Dict:
        """
        获取用户推荐统计
        
        Args:
            user_address: 用户地址
            
        Returns:
            Dict: 推荐统计信息
        """
        # 1. 直接下线数量
        direct_referrals = UserReferral.query.filter_by(
            referrer_address=user_address,
            status='active'
        ).count()
        
        # 2. 总佣金收入
        total_commission = db.session.query(func.sum(CommissionRecord.amount))\
            .filter_by(recipient_address=user_address).scalar() or Decimal('0')
        
        # 3. 本月佣金收入
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_commission = db.session.query(func.sum(CommissionRecord.amount))\
            .filter(
                CommissionRecord.recipient_address == user_address,
                CommissionRecord.created_at >= current_month
            ).scalar() or Decimal('0')
        
        # 4. 推荐链深度统计
        max_depth = self._calculate_referral_chain_depth(user_address)
        
        # 5. 间接下线数量（所有层级）
        total_referrals = self._count_all_referrals(user_address)
        
        return {
            'direct_referrals': direct_referrals,
            'total_referrals': total_referrals,
            'total_commission': float(total_commission),
            'monthly_commission': float(monthly_commission),
            'max_chain_depth': max_depth,
            'referral_rate': float(self.referral_rate),
            'estimated_monthly_potential': self._estimate_monthly_potential(user_address)
        }
    
    def _calculate_referral_chain_depth(self, user_address: str, visited: set = None) -> int:
        """
        计算推荐链最大深度
        
        Args:
            user_address: 用户地址
            visited: 已访问的地址集合
            
        Returns:
            int: 最大深度
        """
        if visited is None:
            visited = set()
        
        if user_address in visited:
            return 0  # 防止循环引用
        
        visited.add(user_address)
        
        # 查找所有直接下线
        direct_referrals = UserReferral.query.filter_by(
            referrer_address=user_address,
            status='active'
        ).all()
        
        if not direct_referrals:
            return 1
        
        max_depth = 0
        for referral in direct_referrals:
            depth = self._calculate_referral_chain_depth(referral.user_address, visited.copy())
            max_depth = max(max_depth, depth)
        
        return max_depth + 1
    
    def _count_all_referrals(self, user_address: str, visited: set = None) -> int:
        """
        计算所有层级的推荐人数
        
        Args:
            user_address: 用户地址
            visited: 已访问的地址集合
            
        Returns:
            int: 总推荐人数
        """
        if visited is None:
            visited = set()
        
        if user_address in visited:
            return 0  # 防止循环引用
        
        visited.add(user_address)
        
        # 查找所有直接下线
        direct_referrals = UserReferral.query.filter_by(
            referrer_address=user_address,
            status='active'
        ).all()
        
        total_count = len(direct_referrals)
        
        # 递归计算间接下线
        for referral in direct_referrals:
            total_count += self._count_all_referrals(referral.user_address, visited.copy())
        
        return total_count
    
    def _estimate_monthly_potential(self, user_address: str) -> float:
        """
        估算月度收益潜力
        
        Args:
            user_address: 用户地址
            
        Returns:
            float: 估算的月度收益潜力
        """
        # 基于历史数据估算
        # 这里可以根据实际业务逻辑进行更复杂的计算
        stats = self.get_referral_statistics(user_address)
        
        # 简单估算：直接下线数 * 平均交易金额 * 佣金率 * 预期月交易次数
        avg_transaction_amount = 1000  # 假设平均交易金额
        expected_monthly_transactions = 2  # 假设每人每月2次交易
        
        potential = (stats['direct_referrals'] * 
                    avg_transaction_amount * 
                    float(self.referral_rate) * 
                    expected_monthly_transactions)
        
        return potential
    
    def get_referral_chain(self, user_address: str, max_levels: int = 10) -> List[Dict]:
        """
        获取推荐链信息
        
        Args:
            user_address: 用户地址
            max_levels: 最大层级数
            
        Returns:
            List[Dict]: 推荐链信息
        """
        chain = []
        current_user = user_address
        level = 0
        
        while level < max_levels:
            # 查找当前用户的推荐人
            referral = UserReferral.query.filter_by(
                user_address=current_user,
                status='active'
            ).first()
            
            if not referral:
                break
            
            # 获取推荐人的统计信息
            referrer_stats = self.get_referral_statistics(referral.referrer_address)
            
            chain.append({
                'level': level + 1,
                'referrer_address': referral.referrer_address,
                'referral_time': referral.referral_time.isoformat() if referral.referral_time else None,
                'referral_code': referral.referral_code,
                'referrer_stats': referrer_stats
            })
            
            current_user = referral.referrer_address
            level += 1
        
        return chain
    
    def get_downline_tree(self, user_address: str, max_levels: int = 5) -> Dict:
        """
        获取下线树结构
        
        Args:
            user_address: 用户地址
            max_levels: 最大层级数
            
        Returns:
            Dict: 下线树结构
        """
        def build_tree(address: str, current_level: int) -> Dict:
            if current_level >= max_levels:
                return {'address': address, 'children': [], 'level': current_level}
            
            # 查找直接下线
            direct_referrals = UserReferral.query.filter_by(
                referrer_address=address,
                status='active'
            ).all()
            
            children = []
            for referral in direct_referrals:
                child_tree = build_tree(referral.user_address, current_level + 1)
                child_tree.update({
                    'referral_time': referral.referral_time.isoformat() if referral.referral_time else None,
                    'referral_code': referral.referral_code
                })
                children.append(child_tree)
            
            return {
                'address': address,
                'children': children,
                'level': current_level,
                'direct_count': len(children)
            }
        
        return build_tree(user_address, 0)
    
    def validate_referral_system_integrity(self) -> Dict:
        """
        验证推荐系统数据完整性
        
        Returns:
            Dict: 验证结果
        """
        issues = []
        
        # 1. 检查循环引用
        all_referrals = UserReferral.query.filter_by(status='active').all()
        for referral in all_referrals:
            if self._would_create_cycle(referral.user_address, referral.referrer_address):
                issues.append(f"循环引用: {referral.user_address} -> {referral.referrer_address}")
        
        # 2. 检查自我引用
        self_referrals = UserReferral.query.filter(
            UserReferral.user_address == UserReferral.referrer_address,
            UserReferral.status == 'active'
        ).all()
        
        for referral in self_referrals:
            issues.append(f"自我引用: {referral.user_address}")
        
        # 3. 检查重复推荐关系
        duplicate_users = db.session.query(UserReferral.user_address)\
            .filter_by(status='active')\
            .group_by(UserReferral.user_address)\
            .having(func.count(UserReferral.user_address) > 1)\
            .all()
        
        for (user_address,) in duplicate_users:
            issues.append(f"重复推荐关系: {user_address}")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'total_referrals': len(all_referrals),
            'checked_at': datetime.utcnow().isoformat()
        }