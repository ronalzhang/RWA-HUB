"""
自动化佣金处理服务
包含佣金自动计算、取现自动处理等功能
实现完全无人参与的分销系统
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from app.extensions import db
from app.models.commission_withdrawal import CommissionWithdrawal
from app.models.commission_config import UserCommissionBalance, CommissionConfig
from app.models.user import User
from app.models.trade import Trade
from app.blockchain.asset_service import AssetService

logger = logging.getLogger(__name__)


class AutoCommissionService:
    """自动化佣金处理服务"""
    
    @staticmethod
    def process_pending_withdrawals():
        """
        自动处理到期的取现申请
        返回处理结果统计
        """
        try:
            # 获取所有可处理的取现申请
            ready_withdrawals = CommissionWithdrawal.get_ready_to_process()
            
            processed_count = 0
            failed_count = 0
            total_amount = 0.0
            results = []
            
            for withdrawal in ready_withdrawals:
                try:
                    # 验证用户余额是否足够
                    user_balance = UserCommissionBalance.query.filter_by(
                        user_address=withdrawal.user_address
                    ).first()
                    
                    if not user_balance or user_balance.available_balance < withdrawal.amount:
                        withdrawal.mark_failed("余额不足")
                        failed_count += 1
                        continue
                    
                    # 处理提现
                    success = AutoCommissionService._process_single_withdrawal(withdrawal)
                    
                    if success:
                        processed_count += 1
                        total_amount += float(withdrawal.amount)
                        results.append({
                            'withdrawal_id': withdrawal.id,
                            'user_address': withdrawal.user_address,
                            'amount': float(withdrawal.amount),
                            'status': 'success'
                        })
                    else:
                        failed_count += 1
                        results.append({
                            'withdrawal_id': withdrawal.id,
                            'user_address': withdrawal.user_address,
                            'amount': float(withdrawal.amount),
                            'status': 'failed'
                        })
                        
                except Exception as e:
                    logger.error(f"处理取现 {withdrawal.id} 失败: {str(e)}")
                    withdrawal.mark_failed(f"处理异常: {str(e)}")
                    failed_count += 1
            
            logger.info(f"取现自动处理完成: 成功 {processed_count} 笔，失败 {failed_count} 笔，总金额 {total_amount}")
            
            return {
                'processed_count': processed_count,
                'failed_count': failed_count,
                'total_amount': total_amount,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"自动处理取现失败: {str(e)}", exc_info=True)
            return {
                'processed_count': 0,
                'failed_count': 0,
                'total_amount': 0.0,
                'error': str(e)
            }
    
    @staticmethod
    def _process_single_withdrawal(withdrawal):
        """
        处理单个取现申请
        包含区块链转账逻辑（当前为模拟实现）
        """
        try:
            # 标记为处理中
            withdrawal.mark_processing()
            
            # 冻结用户余额
            user_balance = UserCommissionBalance.query.filter_by(
                user_address=withdrawal.user_address
            ).first()
            
            if user_balance:
                # 从可用余额转移到冻结余额
                user_balance.available_balance -= withdrawal.amount
                user_balance.frozen_balance += withdrawal.amount
                db.session.commit()
            
            # TODO: 实际的区块链转账逻辑
            # 这里应该调用相应的区块链转账函数
            # 例如：USDC转账到指定地址
            
            # 模拟转账处理
            import uuid
            import time
            
            # 模拟网络延迟
            time.sleep(1)
            
            # 生成模拟交易哈希
            tx_hash = f"0x{uuid.uuid4().hex}"
            
            # 计算手续费（模拟）
            gas_fee = Decimal('0.01')  # 0.01 USDC手续费
            actual_amount = withdrawal.amount - gas_fee
            
            # 模拟转账成功
            success_rate = 0.95  # 95%成功率
            import random
            if random.random() < success_rate:
                # 转账成功
                withdrawal.mark_completed(tx_hash, actual_amount, gas_fee)
                
                # 更新用户余额：解冻金额并记录提现
                if user_balance:
                    user_balance.frozen_balance -= withdrawal.amount
                    user_balance.withdrawn_amount += withdrawal.amount
                    db.session.commit()
                
                logger.info(f"取现 {withdrawal.id} 处理成功: {tx_hash}")
                return True
            else:
                # 转账失败
                withdrawal.mark_failed("区块链转账失败")
                
                # 退还用户余额
                if user_balance:
                    user_balance.available_balance += withdrawal.amount
                    user_balance.frozen_balance -= withdrawal.amount
                    db.session.commit()
                
                logger.warning(f"取现 {withdrawal.id} 转账失败")
                return False
                
        except Exception as e:
            logger.error(f"处理取现 {withdrawal.id} 异常: {str(e)}", exc_info=True)
            
            # 回滚操作，退还用户余额
            try:
                if user_balance:
                    user_balance.available_balance += withdrawal.amount
                    user_balance.frozen_balance -= withdrawal.amount
                    db.session.commit()
            except:
                pass
            
            withdrawal.mark_failed(f"处理异常: {str(e)}")
            return False
    
    @staticmethod
    def auto_update_all_commission_balances():
        """
        自动更新所有用户的佣金余额
        适合定时任务执行
        """
        try:
            # 获取所有有推荐关系的用户
            users_with_referrals = User.query.filter(
                User.referrer_address.isnot(None)
            ).all()
            
            # 获取所有推荐过别人的用户
            referrers = db.session.query(User.referrer_address).distinct().all()
            referrer_addresses = {r[0] for r in referrers if r[0]}
            
            # 合并所有需要更新佣金的用户
            all_addresses = set()
            for user in users_with_referrals:
                all_addresses.add(user.eth_address)
            all_addresses.update(referrer_addresses)
            
            updated_count = 0
            total_commission = 0.0
            
            for address in all_addresses:
                if address:
                    try:
                        # 更新佣金余额
                        balance = AssetService.update_commission_balance(address)
                        if balance:
                            updated_count += 1
                            total_commission += float(balance.total_earned)
                    except Exception as e:
                        logger.error(f"更新用户 {address} 佣金失败: {str(e)}")
            
            logger.info(f"佣金自动更新完成: 更新 {updated_count} 个用户，总佣金 {total_commission}")
            
            return {
                'updated_count': updated_count,
                'total_commission': total_commission,
                'addresses_processed': len(all_addresses)
            }
            
        except Exception as e:
            logger.error(f"自动更新佣金余额失败: {str(e)}", exc_info=True)
            return {
                'updated_count': 0,
                'total_commission': 0.0,
                'error': str(e)
            }
    
    @staticmethod
    def create_auto_withdrawal(user_address, to_address, amount, currency='USDC'):
        """
        创建自动取现申请
        包含余额验证和延迟设置
        """
        try:
            # 验证用户余额
            user_balance = UserCommissionBalance.query.filter_by(
                user_address=user_address
            ).first()
            
            if not user_balance:
                return {'success': False, 'error': '用户佣金余额不存在'}
            
            if user_balance.available_balance < amount:
                return {
                    'success': False, 
                    'error': f'余额不足，可用余额: {user_balance.available_balance}'
                }
            
            # 获取最低提现金额配置
            min_withdraw = CommissionConfig.get_config('min_withdraw_amount', 10.0)
            if amount < min_withdraw:
                return {
                    'success': False,
                    'error': f'提现金额不能少于 {min_withdraw} {currency}'
                }
            
            # 获取延迟时间配置（分钟）
            delay_minutes = CommissionConfig.get_config('withdrawal_delay_minutes', 1)
            
            # 创建提现申请
            withdrawal = CommissionWithdrawal(
                user_address=user_address,
                to_address=to_address,
                amount=Decimal(str(amount)),
                currency=currency,
                delay_minutes=delay_minutes,
                note=f'自动取现申请 - 延迟 {delay_minutes} 分钟'
            )
            
            db.session.add(withdrawal)
            db.session.commit()
            
            logger.info(f"创建自动取现申请: 用户 {user_address}, 金额 {amount} {currency}")
            
            return {
                'success': True,
                'withdrawal_id': withdrawal.id,
                'delay_minutes': delay_minutes,
                'process_at': withdrawal.process_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建自动取现申请失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_commission_summary(user_address):
        """
        获取用户佣金详细信息
        包含分层级的佣金明细
        """
        try:
            # 获取详细的佣金计算结果
            commission_data = AssetService.calculate_unlimited_commission(user_address)
            
            # 获取余额信息
            user_balance = UserCommissionBalance.query.filter_by(
                user_address=user_address
            ).first()
            
            # 获取取现历史
            withdrawals = CommissionWithdrawal.get_user_withdrawals(user_address, limit=10)
            
            # 构建返回数据
            summary = {
                'user_address': user_address,
                'commission_calculation': commission_data,
                'balance': {
                    'total_earned': float(user_balance.total_earned) if user_balance else 0.0,
                    'available_balance': float(user_balance.available_balance) if user_balance else 0.0,
                    'frozen_balance': float(user_balance.frozen_balance) if user_balance else 0.0,
                    'withdrawn_amount': float(user_balance.withdrawn_amount) if user_balance else 0.0
                },
                'recent_withdrawals': [w.to_dict() for w in withdrawals],
                'auto_process_enabled': True,
                'min_withdraw_amount': CommissionConfig.get_config('min_withdraw_amount', 10.0),
                'withdrawal_delay_minutes': CommissionConfig.get_config('withdrawal_delay_minutes', 1)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取佣金摘要失败: {str(e)}", exc_info=True)
            return {
                'user_address': user_address,
                'error': str(e)
            }
    
    @staticmethod
    def run_automation_cycle():
        """
        运行一个完整的自动化周期
        包含佣金更新和取现处理
        """
        try:
            logger.info("开始运行自动化佣金处理周期")
            
            # 1. 更新所有用户佣金余额
            update_result = AutoCommissionService.auto_update_all_commission_balances()
            
            # 2. 处理到期的取现申请
            withdrawal_result = AutoCommissionService.process_pending_withdrawals()
            
            # 汇总结果
            cycle_result = {
                'cycle_time': datetime.utcnow().isoformat(),
                'commission_update': update_result,
                'withdrawal_process': withdrawal_result,
                'success': True
            }
            
            logger.info(f"自动化周期完成: 更新佣金 {update_result['updated_count']} 用户，处理取现 {withdrawal_result['processed_count']} 笔")
            
            return cycle_result
            
        except Exception as e:
            logger.error(f"自动化周期执行失败: {str(e)}", exc_info=True)
            return {
                'cycle_time': datetime.utcnow().isoformat(),
                'success': False,
                'error': str(e)
            } 