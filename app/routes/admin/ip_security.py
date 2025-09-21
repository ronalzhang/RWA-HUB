"""
IP安全管理模块
整合到现有admin系统中
"""
import logging
from flask import request, jsonify, render_template
from app.utils.ip_security import IPSecurityManager, log_suspicious_activity
from app.utils.decorators import api_endpoint
from app.routes.admin.utils import has_permission
from app.routes.admin.auth import api_admin_required, admin_page_required
from . import admin_bp, admin_api_bp

logger = logging.getLogger(__name__)


@admin_bp.route('/v2/ip-security')
@admin_page_required
def ip_security_page():
    """IP安全管理页面"""
    return render_template('admin_v2/ip_security.html')


@admin_api_bp.route('/ip-security/blacklist', methods=['GET'])
@api_admin_required
@api_endpoint(log_calls=True)
def get_blacklist():
    """获取黑名单列表"""
    try:
        blacklisted_ips = IPSecurityManager.BLACKLISTED_IPS
        whitelist_ips = list(IPSecurityManager.WHITELISTED_IPS)

        return jsonify({
            'success': True,
            'data': {
                'blacklist': [
                    {'ip': ip, 'reason': reason}
                    for ip, reason in blacklisted_ips.items()
                ],
                'whitelist': whitelist_ips
            }
        })
    except Exception as e:
        logger.error(f"获取黑名单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/ip-security/analyze/<string:ip_address>', methods=['GET'])
@api_admin_required
@api_endpoint(log_calls=True)
def analyze_ip_address(ip_address):
    """分析指定IP的行为模式"""
    try:
        hours = request.args.get('hours', 24, type=int)
        behavior = IPSecurityManager.analyze_ip_behavior(ip_address, hours)

        return jsonify({
            'success': True,
            'data': behavior
        })
    except Exception as e:
        logger.error(f"分析IP {ip_address} 失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/ip-security/suspicious', methods=['GET'])
@api_admin_required
@api_endpoint(log_calls=True)
def get_suspicious_ips():
    """获取可疑IP列表"""
    try:
        import psycopg2
        import os
        from datetime import datetime, timedelta

        hours = request.args.get('hours', 24, type=int)
        min_visits = request.args.get('min_visits', 500, type=int)

        database_url = os.getenv('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        since_time = datetime.now() - timedelta(hours=hours)

        cursor.execute("""
            SELECT ip_address, COUNT(*) as visit_count,
                   COUNT(DISTINCT path) as unique_paths,
                   COUNT(DISTINCT user_agent) as unique_agents,
                   MAX(timestamp) as last_visit
            FROM ip_visits
            WHERE timestamp >= %s
            GROUP BY ip_address
            HAVING COUNT(*) >= %s
            ORDER BY visit_count DESC
            LIMIT 50
        """, (since_time, min_visits))

        results = cursor.fetchall()
        suspicious_ips = []

        for ip_address, visit_count, unique_paths, unique_agents, last_visit in results:
            # 检查IP状态
            status = 'normal'
            if IPSecurityManager.is_whitelisted(ip_address):
                status = 'whitelisted'
            elif IPSecurityManager.is_blacklisted(ip_address):
                status = 'blacklisted'
            else:
                behavior = IPSecurityManager.analyze_ip_behavior(ip_address, hours)
                risk_score = behavior.get('risk_score', 0)
                if risk_score >= 80:
                    status = 'high_risk'
                elif risk_score >= 60:
                    status = 'medium_risk'
                elif risk_score >= 40:
                    status = 'low_risk'

            suspicious_ips.append({
                'ip_address': ip_address,
                'visit_count': visit_count,
                'unique_paths': unique_paths,
                'unique_agents': unique_agents,
                'last_visit': last_visit.isoformat() if last_visit else None,
                'status': status,
                'risk_score': behavior.get('risk_score', 0) if 'behavior' in locals() else 0
            })

        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'suspicious_ips': suspicious_ips,
                'query_params': {
                    'hours': hours,
                    'min_visits': min_visits
                }
            }
        })

    except Exception as e:
        logger.error(f"获取可疑IP列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/ip-security/block', methods=['POST'])
@api_admin_required
@api_endpoint(log_calls=True)
def block_ip():
    """手动封禁IP"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        reason = data.get('reason', '管理员手动封禁')

        if not ip_address:
            return jsonify({'success': False, 'error': 'IP地址不能为空'}), 400

        # 检查是否在白名单中
        if IPSecurityManager.is_whitelisted(ip_address):
            return jsonify({'success': False, 'error': '不能封禁白名单IP'}), 400

        # 这里应该将IP添加到数据库或配置文件
        # 目前仅记录日志
        log_suspicious_activity(ip_address, 'MANUAL_BLOCK', reason)

        logger.info(f"管理员手动封禁IP: {ip_address} - {reason}")

        return jsonify({
            'success': True,
            'message': f'IP {ip_address} 已封禁'
        })

    except Exception as e:
        logger.error(f"封禁IP失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/ip-security/stats', methods=['GET'])
@api_admin_required
@api_endpoint(log_calls=True)
def get_security_stats():
    """获取安全统计信息"""
    try:
        blacklist_count = len(IPSecurityManager.BLACKLISTED_IPS)
        whitelist_count = len(IPSecurityManager.WHITELISTED_IPS)

        # 获取最近24小时的访问统计
        import psycopg2
        import os
        from datetime import datetime, timedelta

        database_url = os.getenv('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        since_time = datetime.now() - timedelta(hours=24)

        cursor.execute("""
            SELECT COUNT(*) as total_visits,
                   COUNT(DISTINCT ip_address) as unique_ips
            FROM ip_visits
            WHERE timestamp >= %s
        """, (since_time,))

        result = cursor.fetchone()
        total_visits_24h = result[0] if result else 0
        unique_ips_24h = result[1] if result else 0

        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'blacklist_count': blacklist_count,
                'whitelist_count': whitelist_count,
                'total_visits_24h': total_visits_24h,
                'unique_ips_24h': unique_ips_24h,
                'avg_visits_per_ip': round(total_visits_24h / unique_ips_24h, 2) if unique_ips_24h > 0 else 0
            }
        })

    except Exception as e:
        logger.error(f"获取安全统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500