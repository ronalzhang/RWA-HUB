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
        # 不在构造函数中缓存配置值，而是每次实时获取
        pass
        
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
        计算佣金分配 - 聚合递进佣金机制

        Args:
            transaction_amount: 交易金额
            user_address: 用户地址

        Returns:
            Dict: 佣金分配详情
        """
        # 实时获取配置值，确保使用最新的后台设置
        from app.utils.config_manager import ConfigManager
        from app.models.commission_config import CommissionConfig

        # 获取平台费率配置（从后台系统配置）
        platform_fee_rate = Decimal(str(ConfigManager.get_platform_fee_rate()))

        # 获取佣金率配置（从后台系统配置）
        commission_rate_percent = CommissionConfig.get_config('commission_rate', 35.0)
        referral_rate = Decimal(str(commission_rate_percent / 100))

        distribution = {
            'platform_fee': Decimal('0'),
            'referral_commissions': [],
            'total_referral_amount': Decimal('0')
        }

        # 1. 计算平台基础手续费（作为佣金分配的基础）
        base_platform_fee = transaction_amount * platform_fee_rate

        # 2. 聚合递进佣金计算：每级获得上级佣金的配置比例
        current_base = base_platform_fee  # 从平台手续费开始分配
        current_user = user_address
        level = 1

        while current_base > Decimal('0.000001') and level <= 100:  # 精度限制和安全限制
            # 查找当前用户的推荐人
            referral = UserReferral.query.filter_by(
                user_address=current_user,
                status='active'
            ).first()

            if not referral:
                # 没有推荐人，剩余金额归平台
                distribution['platform_fee'] += current_base
                break

            # 计算当前级佣金：上级佣金基数的配置比例
            commission_amount = current_base * referral_rate

            # 记录佣金分配
            distribution['referral_commissions'].append({
                'level': level,
                'referrer_address': referral.referrer_address,
                'commission_amount': commission_amount,
                'base_amount': current_base,
                'rate': referral_rate,
                'user_address': current_user
            })

            distribution['total_referral_amount'] += commission_amount

            # 为下一级准备：当前级佣金成为下一级的基数
            current_base = commission_amount
            current_user = referral.referrer_address
            level += 1

        # 3. 计算平台最终收益：原始手续费减去分配出的佣金
        distribution['platform_fee'] = base_platform_fee - distribution['total_referral_amount']

        logger.debug(f"聚合递进佣金计算完成: 交易金额={transaction_amount}, 基础手续费={base_platform_fee}, "
                    f"分配佣金={distribution['total_referral_amount']}, 平台收益={distribution['platform_fee']}, "
                    f"平台费率={platform_fee_rate*100}%, 佣金率={referral_rate*100}%")

        return distribution

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