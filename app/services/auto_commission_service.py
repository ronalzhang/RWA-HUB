"""
自动佣金服务
实现固定比例佣金分配算法和平台可持续性监控
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.referral import UserReferral, CommissionRecord
from app.models.commission_config import UserCommissionBalance, CommissionConfig
from app.models.trade import Trade
from app.models.asset import Asset
from app.services.unlimited_referral_system import UnlimitedReferralSystem

logger = logging.getLogger(__name__)


class AutoCommissionService:
    """自动佣金服务"""
    
    def __init__(self):
        self.referral_system = UnlimitedReferralSystem()
        self.fixed_referral_rate = Decimal('0.05')  # 固定5%上供比例
        self.platform_sustainability_threshold = Decimal('0.15')  # 平台可持续性阈值15%
        
    def process_batch_commission_records(self, trade_ids: List[int]) -> Dict:
        """
        批量处理佣金记录创建
        
        Args:
            trade_ids: 交易ID列表
            
        Returns:
            Dict: 批量处理结果
        """
        results = {
            'success_count': 0,
            'failed_count': 0,
            'total_commission_amount': Decimal('0'),
            'platform_earnings': Decimal('0'),
            'failed_trades': [],
            'commission_records': []
        }
        
        try:
            for trade_id in trade_ids:
                try:
                    result = self._process_single_trade_commission(trade_id)
                    if result['success']:
                        results['success_count'] += 1
                        results['total_commission_amount'] += result['total_commission']
                        results['platform_earnings'] += result['platform_fee']
                        results['commission_records'].extend(result['commission_records'])
                    else:
                        results['failed_count'] += 1
                        results['failed_trades'].append({
                            'trade_id': trade_id,
                            'error': result['error']
                        })
                        
                except Exception as e:
                    results['failed_count'] += 1
                    results['failed_trades'].append({
                        'trade_id': trade_id,
                        'error': str(e)
                    })
                    logger.error(f"处理交易 {trade_id} 佣金失败: {e}")
            
            # 批量提交数据库更改
            db.session.commit()
            
            logger.info(f"批量佣金处理完成: 成功 {results['success_count']}, 失败 {results['failed_count']}")
            return results
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"批量佣金处理失败: {e}")
            raise
    
    def _process_single_trade_commission(self, trade_id: int) -> Dict:
        """
        处理单个交易的佣金分配
        
        Args:
            trade_id: 交易ID
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 1. 获取交易信息
            trade = Trade.query.get(trade_id)
            if not trade:
                return {'success': False, 'error': f'交易 {trade_id} 不存在'}
            
            # 2. 检查是否已处理过佣金
            existing_commission = CommissionRecord.query.filter_by(transaction_id=trade_id).first()
            if existing_commission:
                return {'success': False, 'error': f'交易 {trade_id} 已处理过佣金'}
            
            # 3. 计算佣金分配
            distribution = self.referral_system.calculate_commission_distribution(
                Decimal(str(trade.total)),
                trade.trader_address
            )
            
            # 4. 创建佣金记录
            commission_records = []
            
            # 创建推荐佣金记录
            for referral_info in distribution['referral_commissions']:
                commission = CommissionRecord(
                    transaction_id=trade_id,
                    asset_id=trade.asset_id,
                    recipient_address=referral_info['referrer_address'],
                    amount=float(referral_info['commission_amount']),
                    currency='USDC',
                    commission_type=f'referral_level_{referral_info["level"]}',
                    status='pending',
                    created_at=datetime.utcnow()
                )
                commission_records.append(commission)
            
            # 创建平台佣金记录
            if distribution['platform_fee'] > 0:
                platform_commission = CommissionRecord(
                    transaction_id=trade_id,
                    asset_id=trade.asset_id,
                    recipient_address='platform',  # 平台地址标识
                    amount=float(distribution['platform_fee']),
                    currency='USDC',
                    commission_type='platform_fee',
                    status='pending',
                    created_at=datetime.utcnow()
                )
                commission_records.append(platform_commission)
            
            # 5. 批量保存佣金记录
            if commission_records:
                db.session.bulk_save_objects(commission_records)
            
            # 6. 更新用户佣金余额
            for referral_info in distribution['referral_commissions']:
                self._update_user_commission_balance_optimized(
                    referral_info['referrer_address'],
                    referral_info['commission_amount']
                )
            
            return {
                'success': True,
                'total_commission': distribution['total_referral_amount'],
                'platform_fee': distribution['platform_fee'],
                'commission_records': [c.to_dict() if hasattr(c, 'to_dict') else str(c) for c in commission_records],
                'referral_levels': len(distribution['referral_commissions'])
            }
            
        except Exception as e:
            logger.error(f"处理交易 {trade_id} 佣金失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _update_user_commission_balance_optimized(self, user_address: str, amount: Decimal):
        """
        优化的用户佣金余额更新
        
        Args:
            user_address: 用户地址
            amount: 佣金金额
        """
        # 使用 ON CONFLICT 或 INSERT ... ON DUPLICATE KEY UPDATE 的思路
        # 先尝试更新，如果不存在则创建
        balance = UserCommissionBalance.query.filter_by(user_address=user_address).first()
        
        if balance:
            # 更新现有记录
            balance.total_earned += amount
            balance.available_balance += amount
            balance.last_updated = datetime.utcnow()
        else:
            # 创建新记录
            balance = UserCommissionBalance(
                user_address=user_address,
                total_earned=amount,
                available_balance=amount,
                withdrawn_amount=Decimal('0'),
                frozen_amount=Decimal('0'),
                currency='USDC',
                last_updated=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            db.session.add(balance)
    
    def get_platform_sustainability_metrics(self) -> Dict:
        """
        获取平台可持续性指标监控
        
        Returns:
            Dict: 平台可持续性指标
        """
        try:
            # 1. 基础统计数据
            total_transactions = Trade.query.count()
            total_transaction_volume = db.session.query(func.sum(Trade.total)).scalar() or Decimal('0')
            
            # 2. 佣金统计
            total_referral_commission = db.session.query(func.sum(CommissionRecord.amount))\
                .filter(CommissionRecord.commission_type.like('referral_%')).scalar() or Decimal('0')
            
            total_platform_fee = db.session.query(func.sum(CommissionRecord.amount))\
                .filter_by(commission_type='platform_fee').scalar() or Decimal('0')
            
            # 3. 计算关键指标
            if total_transaction_volume > 0:
                referral_cost_ratio = total_referral_commission / total_transaction_volume
                platform_profit_ratio = total_platform_fee / total_transaction_volume
                total_commission_ratio = (total_referral_commission + total_platform_fee) / total_transaction_volume
            else:
                referral_cost_ratio = Decimal('0')
                platform_profit_ratio = Decimal('0')
                total_commission_ratio = Decimal('0')
            
            # 4. 活跃用户统计
            active_referrers = db.session.query(func.count(func.distinct(CommissionRecord.recipient_address)))\
                .filter(CommissionRecord.commission_type.like('referral_%')).scalar() or 0
            
            total_users_with_referrals = UserReferral.query.filter_by(status='active').count()
            
            # 5. 时间段分析（最近30天）
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_transactions = Trade.query.filter(Trade.created_at >= thirty_days_ago).count()
            recent_volume = db.session.query(func.sum(Trade.total))\
                .filter(Trade.created_at >= thirty_days_ago).scalar() or Decimal('0')
            
            recent_referral_commission = db.session.query(func.sum(CommissionRecord.amount))\
                .filter(
                    and_(
                        CommissionRecord.commission_type.like('referral_%'),
                        CommissionRecord.created_at >= thirty_days_ago
                    )
                ).scalar() or Decimal('0')
            
            # 6. 可持续性评分计算
            sustainability_score = self._calculate_sustainability_score(
                referral_cost_ratio,
                platform_profit_ratio,
                active_referrers,
                total_users_with_referrals
            )
            
            # 7. 推荐层级分析
            level_analysis = self._analyze_referral_levels()
            
            return {
                'basic_metrics': {
                    'total_transactions': total_transactions,
                    'total_volume': float(total_transaction_volume),
                    'total_referral_commission': float(total_referral_commission),
                    'total_platform_fee': float(total_platform_fee)
                },
                'ratio_metrics': {
                    'referral_cost_ratio': float(referral_cost_ratio),
                    'platform_profit_ratio': float(platform_profit_ratio),
                    'total_commission_ratio': float(total_commission_ratio)
                },
                'user_metrics': {
                    'active_referrers': active_referrers,
                    'total_users_with_referrals': total_users_with_referrals,
                    'referrer_activation_rate': float(active_referrers / max(total_users_with_referrals, 1))
                },
                'recent_metrics': {
                    'recent_transactions': recent_transactions,
                    'recent_volume': float(recent_volume),
                    'recent_referral_commission': float(recent_referral_commission),
                    'recent_growth_rate': float(recent_volume / max(total_transaction_volume - recent_volume, 1))
                },
                'sustainability': {
                    'score': sustainability_score,
                    'status': self._get_sustainability_status(sustainability_score),
                    'recommendations': self._get_sustainability_recommendations(sustainability_score)
                },
                'level_analysis': level_analysis,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取平台可持续性指标失败: {e}")
            raise
    
    def _calculate_sustainability_score(self, referral_cost_ratio: Decimal, 
                                      platform_profit_ratio: Decimal,
                                      active_referrers: int,
                                      total_users: int) -> float:
        """
        计算可持续性评分 (0-100)
        
        Args:
            referral_cost_ratio: 推荐成本比例
            platform_profit_ratio: 平台利润比例
            active_referrers: 活跃推荐人数
            total_users: 总用户数
            
        Returns:
            float: 可持续性评分
        """
        score = 100.0
        
        # 1. 成本控制评分 (40分)
        if referral_cost_ratio > Decimal('0.30'):  # 超过30%成本
            score -= 40
        elif referral_cost_ratio > Decimal('0.20'):  # 超过20%成本
            score -= 20
        elif referral_cost_ratio > Decimal('0.15'):  # 超过15%成本
            score -= 10
        
        # 2. 平台盈利评分 (30分)
        if platform_profit_ratio < Decimal('0.05'):  # 低于5%利润
            score -= 30
        elif platform_profit_ratio < Decimal('0.10'):  # 低于10%利润
            score -= 15
        elif platform_profit_ratio < Decimal('0.15'):  # 低于15%利润
            score -= 5
        
        # 3. 用户活跃度评分 (20分)
        if total_users > 0:
            activation_rate = active_referrers / total_users
            if activation_rate < 0.1:  # 低于10%激活率
                score -= 20
            elif activation_rate < 0.2:  # 低于20%激活率
                score -= 10
            elif activation_rate < 0.3:  # 低于30%激活率
                score -= 5
        
        # 4. 增长潜力评分 (10分)
        if active_referrers < 10:  # 活跃推荐人太少
            score -= 10
        elif active_referrers < 50:
            score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _get_sustainability_status(self, score: float) -> str:
        """获取可持续性状态"""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'warning'
        else:
            return 'critical'
    
    def _get_sustainability_recommendations(self, score: float) -> List[str]:
        """获取可持续性建议"""
        recommendations = []
        
        if score < 40:
            recommendations.extend([
                '立即调整佣金比例，降低推荐成本',
                '增加平台基础费用以提高盈利能力',
                '限制推荐层级深度以控制成本'
            ])
        elif score < 60:
            recommendations.extend([
                '监控佣金成本比例，确保不超过20%',
                '优化用户激活策略，提高推荐人活跃度',
                '考虑引入阶梯式佣金比例'
            ])
        elif score < 80:
            recommendations.extend([
                '保持当前佣金策略，继续监控指标',
                '扩大用户基数以提高整体收益',
                '优化推荐人培训和激励机制'
            ])
        else:
            recommendations.extend([
                '当前策略表现优秀，可考虑适度扩展',
                '继续优化用户体验以维持增长',
                '考虑引入更多激励机制'
            ])
        
        return recommendations
    
    def _analyze_referral_levels(self) -> Dict:
        """分析推荐层级分布"""
        try:
            # 统计各层级的佣金分布
            level_stats = db.session.query(
                CommissionRecord.commission_type,
                func.count(CommissionRecord.id).label('count'),
                func.sum(CommissionRecord.amount).label('total_amount'),
                func.avg(CommissionRecord.amount).label('avg_amount')
            ).filter(
                CommissionRecord.commission_type.like('referral_level_%')
            ).group_by(CommissionRecord.commission_type).all()
            
            level_analysis = {}
            total_referral_records = 0
            total_referral_amount = Decimal('0')
            
            for stat in level_stats:
                level_num = stat.commission_type.replace('referral_level_', '')
                level_analysis[f'level_{level_num}'] = {
                    'count': stat.count,
                    'total_amount': float(stat.total_amount or 0),
                    'avg_amount': float(stat.avg_amount or 0),
                    'percentage': 0  # 将在后面计算
                }
                total_referral_records += stat.count
                total_referral_amount += Decimal(str(stat.total_amount or 0))
            
            # 计算百分比
            for level_key in level_analysis:
                if total_referral_amount > 0:
                    level_analysis[level_key]['percentage'] = float(
                        Decimal(str(level_analysis[level_key]['total_amount'])) / total_referral_amount * 100
                    )
            
            # 计算平均推荐深度
            max_level = 0
            for level_key in level_analysis:
                level_num = int(level_key.replace('level_', ''))
                max_level = max(max_level, level_num)
            
            return {
                'level_distribution': level_analysis,
                'max_level': max_level,
                'total_referral_records': total_referral_records,
                'total_referral_amount': float(total_referral_amount),
                'avg_referral_depth': self._calculate_avg_referral_depth()
            }
            
        except Exception as e:
            logger.error(f"分析推荐层级失败: {e}")
            return {}
    
    def _calculate_avg_referral_depth(self) -> float:
        """计算平均推荐深度"""
        try:
            # 获取所有有推荐关系的用户
            users_with_referrals = db.session.query(UserReferral.referrer_address)\
                .filter_by(status='active')\
                .distinct().all()
            
            total_depth = 0
            user_count = 0
            
            for (user_address,) in users_with_referrals:
                depth = self.referral_system._calculate_referral_chain_depth(user_address)
                total_depth += depth
                user_count += 1
            
            return total_depth / max(user_count, 1)
            
        except Exception as e:
            logger.error(f"计算平均推荐深度失败: {e}")
            return 0.0
    
    def optimize_commission_rates(self) -> Dict:
        """
        基于平台可持续性指标优化佣金比例
        
        Returns:
            Dict: 优化建议
        """
        try:
            metrics = self.get_platform_sustainability_metrics()
            current_rate = float(self.fixed_referral_rate)
            
            recommendations = {
                'current_rate': current_rate,
                'recommended_rate': current_rate,
                'reason': '',
                'expected_impact': {},
                'should_adjust': False
            }
            
            sustainability_score = metrics['sustainability']['score']
            referral_cost_ratio = metrics['ratio_metrics']['referral_cost_ratio']
            platform_profit_ratio = metrics['ratio_metrics']['platform_profit_ratio']
            
            # 基于可持续性评分调整建议
            if sustainability_score < 40:
                # 严重情况：大幅降低佣金比例
                recommended_rate = max(0.02, current_rate * 0.6)  # 降低40%，最低2%
                recommendations.update({
                    'recommended_rate': recommended_rate,
                    'reason': '平台可持续性评分过低，需要大幅降低佣金比例以控制成本',
                    'should_adjust': True
                })
            elif sustainability_score < 60:
                # 警告情况：适度降低佣金比例
                recommended_rate = max(0.03, current_rate * 0.8)  # 降低20%，最低3%
                recommendations.update({
                    'recommended_rate': recommended_rate,
                    'reason': '平台可持续性需要改善，建议适度降低佣金比例',
                    'should_adjust': True
                })
            elif sustainability_score > 80 and platform_profit_ratio > 0.20:
                # 优秀情况：可以考虑适度提高佣金比例
                recommended_rate = min(0.08, current_rate * 1.2)  # 提高20%，最高8%
                recommendations.update({
                    'recommended_rate': recommended_rate,
                    'reason': '平台表现优秀且盈利充足，可以适度提高佣金比例以激励用户',
                    'should_adjust': True
                })
            else:
                recommendations['reason'] = '当前佣金比例合适，建议保持现状'
            
            # 计算预期影响
            if recommendations['should_adjust']:
                rate_change = recommended_rate - current_rate
                expected_cost_change = rate_change * metrics['basic_metrics']['total_volume']
                
                recommendations['expected_impact'] = {
                    'rate_change_percentage': (rate_change / current_rate) * 100,
                    'expected_cost_change': float(expected_cost_change),
                    'expected_sustainability_score_change': self._estimate_score_change(
                        sustainability_score, rate_change
                    )
                }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"优化佣金比例失败: {e}")
            raise
    
    def _estimate_score_change(self, current_score: float, rate_change: float) -> float:
        """估算评分变化"""
        # 简单的线性估算，实际可以更复杂
        if rate_change < 0:  # 降低佣金比例
            return min(20, abs(rate_change) * 400)  # 最多提高20分
        else:  # 提高佣金比例
            return max(-15, -rate_change * 300)  # 最多降低15分
    
    def generate_commission_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        生成佣金报表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 佣金报表
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        try:
            # 基础查询条件
            base_query = CommissionRecord.query.filter(
                and_(
                    CommissionRecord.created_at >= start_date,
                    CommissionRecord.created_at <= end_date
                )
            )
            
            # 1. 总体统计
            total_records = base_query.count()
            total_amount = base_query.with_entities(func.sum(CommissionRecord.amount)).scalar() or 0
            
            # 2. 按类型统计
            type_stats = base_query.with_entities(
                CommissionRecord.commission_type,
                func.count(CommissionRecord.id).label('count'),
                func.sum(CommissionRecord.amount).label('amount')
            ).group_by(CommissionRecord.commission_type).all()
            
            # 3. 按状态统计
            status_stats = base_query.with_entities(
                CommissionRecord.status,
                func.count(CommissionRecord.id).label('count'),
                func.sum(CommissionRecord.amount).label('amount')
            ).group_by(CommissionRecord.status).all()
            
            # 4. 按日期统计
            daily_stats = base_query.with_entities(
                func.date(CommissionRecord.created_at).label('date'),
                func.count(CommissionRecord.id).label('count'),
                func.sum(CommissionRecord.amount).label('amount')
            ).group_by(func.date(CommissionRecord.created_at)).all()
            
            # 5. 顶级推荐人统计
            top_referrers = base_query.filter(
                CommissionRecord.commission_type.like('referral_%')
            ).with_entities(
                CommissionRecord.recipient_address,
                func.count(CommissionRecord.id).label('count'),
                func.sum(CommissionRecord.amount).label('amount')
            ).group_by(CommissionRecord.recipient_address)\
             .order_by(func.sum(CommissionRecord.amount).desc())\
             .limit(10).all()
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': (end_date - start_date).days
                },
                'summary': {
                    'total_records': total_records,
                    'total_amount': float(total_amount),
                    'avg_amount_per_record': float(total_amount / max(total_records, 1))
                },
                'by_type': [
                    {
                        'type': stat.commission_type,
                        'count': stat.count,
                        'amount': float(stat.amount or 0),
                        'percentage': float((stat.amount or 0) / max(total_amount, 1) * 100)
                    }
                    for stat in type_stats
                ],
                'by_status': [
                    {
                        'status': stat.status,
                        'count': stat.count,
                        'amount': float(stat.amount or 0),
                        'percentage': float((stat.amount or 0) / max(total_amount, 1) * 100)
                    }
                    for stat in status_stats
                ],
                'daily_trend': [
                    {
                        'date': stat.date.isoformat(),
                        'count': stat.count,
                        'amount': float(stat.amount or 0)
                    }
                    for stat in daily_stats
                ],
                'top_referrers': [
                    {
                        'address': stat.recipient_address,
                        'count': stat.count,
                        'amount': float(stat.amount or 0)
                    }
                    for stat in top_referrers
                ],
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成佣金报表失败: {e}")
            raise