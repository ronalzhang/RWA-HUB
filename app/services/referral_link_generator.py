"""
推荐链接生成器
实现推荐链接生成、跟踪和统计功能
"""

import hashlib
import logging
import random
import string
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs

from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.shortlink import ShortLink
from app.models.referral import UserReferral
from app.models.commission_config import CommissionConfig
from app.models.share_message import ShareMessage

logger = logging.getLogger(__name__)


class ReferralLinkGenerator:
    """推荐链接生成器"""
    
    def __init__(self):
        self.base_url = self._get_base_url()
        self.default_expiry_days = 365  # 默认链接有效期1年
        
    def _get_base_url(self) -> str:
        """获取基础URL"""
        try:
            base_url = CommissionConfig.get_config('BASE_URL', 'https://rwa-hub.com')
            return base_url.rstrip('/')
        except:
            return 'https://rwa-hub.com'
    
    def generate_referral_link(self, referrer_address: str, 
                             custom_code: str = None,
                             expiry_days: int = None,
                             campaign: str = None) -> Dict:
        """
        生成推荐链接
        
        Args:
            referrer_address: 推荐人钱包地址
            custom_code: 自定义推荐码（可选）
            expiry_days: 有效期天数（可选）
            campaign: 活动标识（可选）
            
        Returns:
            Dict: 推荐链接信息
        """
        try:
            # 1. 生成或验证推荐码
            if custom_code:
                referral_code = self._validate_custom_code(custom_code)
            else:
                referral_code = self._generate_referral_code(referrer_address)
            
            # 2. 检查推荐码唯一性
            existing_link = ShortLink.query.filter_by(code=referral_code).first()
            if existing_link:
                if existing_link.creator_address == referrer_address:
                    # 返回现有链接
                    return self._format_link_response(existing_link, campaign)
                else:
                    # 推荐码冲突，重新生成
                    referral_code = self._generate_referral_code(referrer_address, force_unique=True)
            
            # 3. 构建原始URL
            original_url = self._build_original_url(referral_code, campaign)
            
            # 4. 设置过期时间
            expiry_days = expiry_days or self.default_expiry_days
            expires_at = datetime.utcnow() + timedelta(days=expiry_days)
            
            # 5. 创建短链接记录
            short_link = ShortLink(
                code=referral_code,
                original_url=original_url,
                creator_address=referrer_address,
                expires_at=expires_at,
                click_count=0,
                created_at=datetime.utcnow()
            )
            
            db.session.add(short_link)
            db.session.commit()
            
            logger.info(f"推荐链接创建成功: {referrer_address} -> {referral_code}")
            
            return self._format_link_response(short_link, campaign)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"生成推荐链接失败: {e}")
            raise
    
    def _validate_custom_code(self, custom_code: str) -> str:
        """
        验证自定义推荐码
        
        Args:
            custom_code: 自定义推荐码
            
        Returns:
            str: 验证后的推荐码
            
        Raises:
            ValueError: 当推荐码无效时
        """
        # 清理和验证推荐码
        code = custom_code.strip().upper()
        
        # 检查长度
        if len(code) < 3 or len(code) > 20:
            raise ValueError("推荐码长度必须在3-20个字符之间")
        
        # 检查字符
        if not code.replace('_', '').replace('-', '').isalnum():
            raise ValueError("推荐码只能包含字母、数字、下划线和连字符")
        
        # 检查是否为保留词
        reserved_words = ['ADMIN', 'API', 'WWW', 'SYSTEM', 'PLATFORM', 'TEST']
        if code in reserved_words:
            raise ValueError("推荐码不能使用保留词")
        
        return code
    
    def _generate_referral_code(self, referrer_address: str, force_unique: bool = False) -> str:
        """
        生成推荐码
        
        Args:
            referrer_address: 推荐人地址
            force_unique: 是否强制唯一
            
        Returns:
            str: 推荐码
        """
        # 基于地址和时间戳生成基础码
        timestamp = int(time.time())
        raw_data = f"{referrer_address}_{timestamp}"
        
        if force_unique:
            # 添加随机数确保唯一性
            raw_data += f"_{random.randint(1000, 9999)}"
        
        # 生成哈希
        hash_object = hashlib.md5(raw_data.encode())
        base_code = hash_object.hexdigest()[:8].upper()
        
        # 如果需要确保唯一性，添加随机后缀
        attempts = 0
        while attempts < 10:
            test_code = base_code
            if attempts > 0:
                test_code += str(random.randint(10, 99))
            
            # 检查唯一性
            existing = ShortLink.query.filter_by(code=test_code).first()
            if not existing:
                return test_code
            
            attempts += 1
        
        # 如果仍然冲突，使用完全随机的码
        return self._generate_random_code()
    
    def _generate_random_code(self, length: int = 8) -> str:
        """生成完全随机的推荐码"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(length))
            existing = ShortLink.query.filter_by(code=code).first()
            if not existing:
                return code
    
    def _build_original_url(self, referral_code: str, campaign: str = None) -> str:
        """构建原始URL"""
        params = {'ref': referral_code}
        if campaign:
            params['campaign'] = campaign
        
        # 构建查询字符串
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}?{query_string}"
    
    def _format_link_response(self, short_link: ShortLink, campaign: str = None) -> Dict:
        """格式化链接响应"""
        short_url = f"{self.base_url}/r/{short_link.code}"
        
        return {
            'referral_code': short_link.code,
            'short_url': short_url,
            'original_url': short_link.original_url,
            'qr_code_url': f"{self.base_url}/api/qr/{short_link.code}",
            'creator_address': short_link.creator_address,
            'created_at': short_link.created_at.isoformat() if short_link.created_at else None,
            'expires_at': short_link.expires_at.isoformat() if short_link.expires_at else None,
            'click_count': short_link.click_count,
            'campaign': campaign,
            'share_text': self._generate_share_text(short_link.code, campaign),
            'social_links': self._generate_social_links(short_url, campaign)
        }
    
    def _generate_share_text(self, referral_code: str, campaign: str = None) -> Dict:
        """生成分享文案"""
        try:
            # 从配置获取分享文案模板
            share_templates = CommissionConfig.get_config('share_templates', {
                'default': '🚀 发现超值投资机会！通过我的推荐链接注册，我们都能获得丰厚奖励！',
                'wechat': '💰 独家投资机会分享！点击链接了解详情，还有推荐奖励等你拿！',
                'weibo': '🔥 热门投资项目推荐！通过专属链接注册即享优惠，快来一起赚钱！',
                'telegram': '💎 Premium investment opportunity! Join through my referral link for exclusive rewards!'
            })
            
            base_text = share_templates.get('default', '通过我的推荐链接注册，获得专属奖励！')
            
            # 添加推荐码信息
            if campaign:
                base_text += f" 活动代码：{campaign}"
            
            base_text += f" 推荐码：{referral_code}"
            
            return {
                'default': base_text,
                'wechat': share_templates.get('wechat', base_text),
                'weibo': share_templates.get('weibo', base_text),
                'telegram': share_templates.get('telegram', base_text),
                'custom': f"邀请码 {referral_code} - {base_text}"
            }
            
        except Exception as e:
            logger.error(f"生成分享文案失败: {e}")
            return {
                'default': f'推荐码：{referral_code} - 通过我的推荐链接注册，获得专属奖励！'
            }
    
    def _generate_social_links(self, short_url: str, campaign: str = None) -> Dict:
        """生成社交媒体分享链接"""
        from urllib.parse import quote
        
        share_text = f"发现超值投资机会！{short_url}"
        if campaign:
            share_text += f" #{campaign}"
        
        encoded_text = quote(share_text)
        encoded_url = quote(short_url)
        
        return {
            'wechat': f"weixin://dl/chat?{encoded_text}",
            'weibo': f"https://service.weibo.com/share/share.php?url={encoded_url}&title={encoded_text}",
            'qq': f"https://connect.qq.com/widget/shareqq/index.html?url={encoded_url}&title={encoded_text}",
            'telegram': f"https://t.me/share/url?url={encoded_url}&text={encoded_text}",
            'twitter': f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_text}",
            'facebook': f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
            'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"
        }
    
    def track_link_click(self, referral_code: str, visitor_info: Dict = None) -> Dict:
        """
        跟踪链接点击
        
        Args:
            referral_code: 推荐码
            visitor_info: 访客信息（IP、User-Agent等）
            
        Returns:
            Dict: 跟踪结果
        """
        try:
            # 1. 查找短链接
            short_link = ShortLink.query.filter_by(code=referral_code).first()
            if not short_link:
                return {'success': False, 'error': '推荐链接不存在'}
            
            # 2. 检查链接是否过期
            if short_link.is_expired():
                return {'success': False, 'error': '推荐链接已过期'}
            
            # 3. 增加点击计数
            short_link.increment_click()
            
            # 4. 记录详细的点击信息（如果需要）
            if visitor_info:
                self._record_click_details(referral_code, visitor_info)
            
            # 5. 返回推荐人信息
            return {
                'success': True,
                'referrer_address': short_link.creator_address,
                'referral_code': referral_code,
                'original_url': short_link.original_url,
                'click_count': short_link.click_count,
                'created_at': short_link.created_at.isoformat() if short_link.created_at else None
            }
            
        except Exception as e:
            logger.error(f"跟踪链接点击失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _record_click_details(self, referral_code: str, visitor_info: Dict):
        """记录点击详情（可选功能）"""
        try:
            # 这里可以记录更详细的点击信息到单独的表
            # 例如：IP地址、User-Agent、点击时间、地理位置等
            # 为了简化，这里只记录到日志
            logger.info(f"推荐链接点击: {referral_code}, 访客信息: {visitor_info}")
        except Exception as e:
            logger.error(f"记录点击详情失败: {e}")
    
    def get_link_statistics(self, referrer_address: str) -> Dict:
        """
        获取推荐链接统计
        
        Args:
            referrer_address: 推荐人地址
            
        Returns:
            Dict: 链接统计信息
        """
        try:
            # 1. 获取用户的所有推荐链接
            user_links = ShortLink.query.filter_by(creator_address=referrer_address).all()
            
            # 2. 计算总体统计
            total_links = len(user_links)
            total_clicks = sum(link.click_count for link in user_links)
            active_links = len([link for link in user_links if not link.is_expired()])
            
            # 3. 获取最受欢迎的链接
            popular_links = sorted(user_links, key=lambda x: x.click_count, reverse=True)[:5]
            
            # 4. 计算转化统计
            successful_referrals = UserReferral.query.filter_by(
                referrer_address=referrer_address,
                status='active'
            ).count()
            
            conversion_rate = (successful_referrals / max(total_clicks, 1)) * 100
            
            # 5. 时间段分析
            now = datetime.utcnow()
            recent_links = [link for link in user_links 
                          if link.created_at and link.created_at >= now - timedelta(days=30)]
            recent_clicks = sum(link.click_count for link in recent_links)
            
            return {
                'summary': {
                    'total_links': total_links,
                    'active_links': active_links,
                    'expired_links': total_links - active_links,
                    'total_clicks': total_clicks,
                    'successful_referrals': successful_referrals,
                    'conversion_rate': round(conversion_rate, 2)
                },
                'popular_links': [
                    {
                        'code': link.code,
                        'clicks': link.click_count,
                        'created_at': link.created_at.isoformat() if link.created_at else None,
                        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
                        'is_expired': link.is_expired()
                    }
                    for link in popular_links
                ],
                'recent_activity': {
                    'new_links_30d': len(recent_links),
                    'clicks_30d': recent_clicks,
                    'avg_clicks_per_link': round(recent_clicks / max(len(recent_links), 1), 2)
                },
                'performance_metrics': {
                    'avg_clicks_per_link': round(total_clicks / max(total_links, 1), 2),
                    'best_performing_code': popular_links[0].code if popular_links else None,
                    'best_performing_clicks': popular_links[0].click_count if popular_links else 0
                }
            }
            
        except Exception as e:
            logger.error(f"获取链接统计失败: {e}")
            raise
    
    def batch_generate_links(self, referrer_address: str, count: int, 
                           prefix: str = None, campaign: str = None) -> List[Dict]:
        """
        批量生成推荐链接
        
        Args:
            referrer_address: 推荐人地址
            count: 生成数量
            prefix: 推荐码前缀
            campaign: 活动标识
            
        Returns:
            List[Dict]: 生成的链接列表
        """
        if count > 100:
            raise ValueError("单次批量生成数量不能超过100个")
        
        links = []
        for i in range(count):
            try:
                custom_code = None
                if prefix:
                    custom_code = f"{prefix}{i+1:03d}"  # 例如：PROMO001, PROMO002
                
                link = self.generate_referral_link(
                    referrer_address=referrer_address,
                    custom_code=custom_code,
                    campaign=campaign
                )
                links.append(link)
                
            except Exception as e:
                logger.error(f"批量生成第{i+1}个链接失败: {e}")
                links.append({'error': str(e), 'index': i+1})
        
        return links
    
    def cleanup_expired_links(self, days_after_expiry: int = 30) -> Dict:
        """
        清理过期链接
        
        Args:
            days_after_expiry: 过期后多少天删除
            
        Returns:
            Dict: 清理结果
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_after_expiry)
            
            # 查找需要删除的过期链接
            expired_links = ShortLink.query.filter(
                and_(
                    ShortLink.expires_at < cutoff_date,
                    ShortLink.expires_at.isnot(None)
                )
            ).all()
            
            deleted_count = len(expired_links)
            
            # 删除过期链接
            for link in expired_links:
                db.session.delete(link)
            
            db.session.commit()
            
            logger.info(f"清理过期链接完成，删除 {deleted_count} 个链接")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"清理过期链接失败: {e}")
            raise
    
    def generate_qr_code_data(self, referral_code: str) -> Dict:
        """
        生成二维码数据
        
        Args:
            referral_code: 推荐码
            
        Returns:
            Dict: 二维码数据
        """
        try:
            short_link = ShortLink.query.filter_by(code=referral_code).first()
            if not short_link:
                raise ValueError("推荐链接不存在")
            
            short_url = f"{self.base_url}/r/{referral_code}"
            
            return {
                'url': short_url,
                'referral_code': referral_code,
                'creator_address': short_link.creator_address,
                'qr_text': short_url,
                'size': '200x200',  # 默认尺寸
                'format': 'PNG'
            }
            
        except Exception as e:
            logger.error(f"生成二维码数据失败: {e}")
            raise
    
    def validate_referral_code_uniqueness(self, code: str, exclude_address: str = None) -> bool:
        """
        验证推荐码唯一性
        
        Args:
            code: 推荐码
            exclude_address: 排除的地址（用于更新时检查）
            
        Returns:
            bool: 是否唯一
        """
        query = ShortLink.query.filter_by(code=code)
        
        if exclude_address:
            query = query.filter(ShortLink.creator_address != exclude_address)
        
        existing = query.first()
        return existing is None