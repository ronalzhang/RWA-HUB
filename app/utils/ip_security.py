"""
IP安全管理模块
用于检测和防御恶意IP访问
"""
import logging
from flask import request, jsonify, g
from functools import wraps
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import psycopg2
from app.extensions import db
from app.models.ip_visit import IPVisit
import os

logger = logging.getLogger(__name__)

class IPSecurityManager:
    """IP安全管理器"""

    # 黑名单IP列表
    BLACKLISTED_IPS = {
        '61.149.75.133': '恶意爬虫 - 高频API访问',
        # 可以添加更多恶意IP
    }

    # 白名单IP列表（管理员和服务器IP）
    WHITELISTED_IPS = {
        '156.232.13.240',  # 服务器IP
        '127.0.0.1',       # 本地IP
        'localhost',       # 本地访问
    }

    # API访问限制配置
    API_RATE_LIMITS = {
        'default': {'requests': 60, 'window': 60},      # 默认：60次/分钟
        'assets': {'requests': 30, 'window': 60},       # 资产接口：30次/分钟
        'trades': {'requests': 20, 'window': 60},       # 交易接口：20次/分钟
        'admin': {'requests': 10, 'window': 60},        # 管理接口：10次/分钟
        'realtime': {'requests': 10, 'window': 60},     # 实时数据：10次/分钟
    }

    @classmethod
    def is_blacklisted(cls, ip_address: str) -> bool:
        """检查IP是否在黑名单中"""
        return ip_address in cls.BLACKLISTED_IPS

    @classmethod
    def is_whitelisted(cls, ip_address: str) -> bool:
        """检查IP是否在白名单中"""
        return ip_address in cls.WHITELISTED_IPS

    @classmethod
    def get_client_ip(cls) -> str:
        """获取客户端真实IP地址"""
        # 检查代理头
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or 'unknown'

    @classmethod
    def analyze_ip_behavior(cls, ip_address: str, hours: int = 24) -> Dict:
        """分析IP在指定时间内的行为模式"""
        try:
            database_url = os.getenv('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()

            # 获取指定时间内的访问记录
            since_time = datetime.now() - timedelta(hours=hours)

            cursor.execute("""
                SELECT COUNT(*) as total_visits,
                       COUNT(DISTINCT path) as unique_paths,
                       COUNT(DISTINCT user_agent) as unique_agents
                FROM ip_visits
                WHERE ip_address = %s AND timestamp >= %s
            """, (ip_address, since_time))

            result = cursor.fetchone()
            total_visits = result[0] if result else 0
            unique_paths = result[1] if result else 0
            unique_agents = result[2] if result else 0

            # 计算风险评分
            risk_score = cls._calculate_risk_score(
                total_visits, unique_paths, unique_agents, hours
            )

            conn.close()

            return {
                'total_visits': total_visits,
                'unique_paths': unique_paths,
                'unique_agents': unique_agents,
                'visits_per_hour': total_visits / hours,
                'risk_score': risk_score,
                'threat_level': cls._get_threat_level(risk_score)
            }

        except Exception as e:
            logger.error(f"分析IP行为失败: {e}")
            return {'error': str(e)}

    @classmethod
    def _calculate_risk_score(cls, total_visits: int, unique_paths: int,
                            unique_agents: int, hours: int) -> int:
        """计算IP风险评分（0-100）"""
        score = 0

        # 访问频率评分（最高30分）
        visits_per_hour = total_visits / hours
        if visits_per_hour > 100:
            score += 30
        elif visits_per_hour > 50:
            score += 20
        elif visits_per_hour > 20:
            score += 10

        # 路径多样性评分（最高20分）
        if unique_paths > 50:
            score += 20
        elif unique_paths > 20:
            score += 15
        elif unique_paths > 10:
            score += 10

        # User-Agent多样性评分（最高15分）
        if unique_agents == 1:
            score += 15  # 只使用一个User-Agent可疑
        elif unique_agents > 10:
            score += 10  # 使用过多User-Agent也可疑

        # 特殊检查
        if total_visits > 1000:
            score += 35  # 大量访问

        return min(score, 100)

    @classmethod
    def _get_threat_level(cls, risk_score: int) -> str:
        """根据风险评分确定威胁等级"""
        if risk_score >= 80:
            return 'HIGH'
        elif risk_score >= 60:
            return 'MEDIUM'
        elif risk_score >= 40:
            return 'LOW'
        else:
            return 'SAFE'


def ip_security_check(allow_blacklisted: bool = False):
    """IP安全检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = IPSecurityManager.get_client_ip()

            # 白名单检查
            if IPSecurityManager.is_whitelisted(client_ip):
                return f(*args, **kwargs)

            # 黑名单检查
            if not allow_blacklisted and IPSecurityManager.is_blacklisted(client_ip):
                reason = IPSecurityManager.BLACKLISTED_IPS.get(client_ip, '未知原因')
                logger.warning(f"阻止黑名单IP访问: {client_ip} - {reason}")
                return jsonify({
                    'error': 'Access denied',
                    'message': 'Your IP has been blocked due to suspicious activity',
                    'code': 'IP_BLOCKED'
                }), 403

            # 存储IP信息到g对象，供后续使用
            g.client_ip = client_ip
            g.ip_whitelisted = IPSecurityManager.is_whitelisted(client_ip)
            g.ip_blacklisted = IPSecurityManager.is_blacklisted(client_ip)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def enhanced_rate_limit(category: str = 'default'):
    """增强的访问频率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = IPSecurityManager.get_client_ip()

            # 白名单IP跳过限制
            if IPSecurityManager.is_whitelisted(client_ip):
                return f(*args, **kwargs)

            # 黑名单IP直接拒绝
            if IPSecurityManager.is_blacklisted(client_ip):
                return jsonify({
                    'error': 'Access denied',
                    'message': 'IP blocked',
                    'code': 'IP_BLOCKED'
                }), 403

            # 获取限制配置
            limit_config = IPSecurityManager.API_RATE_LIMITS.get(
                category, IPSecurityManager.API_RATE_LIMITS['default']
            )

            # 检查访问频率
            behavior = IPSecurityManager.analyze_ip_behavior(client_ip, hours=1)
            if behavior.get('visits_per_hour', 0) > limit_config['requests']:
                logger.warning(f"IP {client_ip} 超过访问频率限制: {behavior['visits_per_hour']}/小时")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limit_config["requests"]} per hour',
                    'code': 'RATE_LIMIT_EXCEEDED'
                }), 429

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_suspicious_activity(ip_address: str, activity_type: str, details: str):
    """记录可疑活动"""
    logger.warning(f"可疑活动 - IP: {ip_address}, 类型: {activity_type}, 详情: {details}")

    # 可以添加到数据库记录中
    try:
        # 这里可以添加数据库记录逻辑
        pass
    except Exception as e:
        logger.error(f"记录可疑活动失败: {e}")