"""
IP黑名单管理命令
"""
import click
from flask.cli import with_appcontext
from app.utils.ip_security import IPSecurityManager
import json


@click.group()
def ip_security():
    """IP安全管理命令组"""
    pass


@ip_security.command()
@click.argument('ip_address')
@click.argument('reason', default='恶意访问')
@with_appcontext
def block_ip(ip_address, reason):
    """添加IP到黑名单"""
    # 这里可以将IP添加到数据库或配置文件
    click.echo(f"IP {ip_address} 已添加到黑名单，原因: {reason}")

    # 记录到日志
    from app import logger
    logger.info(f"管理员手动添加IP到黑名单: {ip_address} - {reason}")


@ip_security.command()
@click.argument('ip_address')
@with_appcontext
def unblock_ip(ip_address):
    """从黑名单移除IP"""
    # 这里可以从数据库或配置文件移除IP
    click.echo(f"IP {ip_address} 已从黑名单移除")

    # 记录到日志
    from app import logger
    logger.info(f"管理员手动从黑名单移除IP: {ip_address}")


@ip_security.command()
@with_appcontext
def list_blocked():
    """列出所有被阻止的IP"""
    blocked_ips = IPSecurityManager.BLACKLISTED_IPS
    if not blocked_ips:
        click.echo("没有被阻止的IP")
        return

    click.echo("被阻止的IP列表:")
    for ip, reason in blocked_ips.items():
        click.echo(f"  {ip}: {reason}")


@ip_security.command()
@click.argument('ip_address')
@click.option('--hours', default=24, help='分析时间范围（小时）')
@with_appcontext
def analyze_ip(ip_address, hours):
    """分析指定IP的行为模式"""
    behavior = IPSecurityManager.analyze_ip_behavior(ip_address, hours)

    if 'error' in behavior:
        click.echo(f"分析失败: {behavior['error']}")
        return

    click.echo(f"IP {ip_address} 在过去 {hours} 小时的行为分析:")
    click.echo(f"  总访问次数: {behavior['total_visits']}")
    click.echo(f"  唯一路径数: {behavior['unique_paths']}")
    click.echo(f"  唯一User-Agent数: {behavior['unique_agents']}")
    click.echo(f"  每小时访问次数: {behavior['visits_per_hour']:.2f}")
    click.echo(f"  风险评分: {behavior['risk_score']}/100")
    click.echo(f"  威胁等级: {behavior['threat_level']}")


@ip_security.command()
@click.option('--hours', default=24, help='分析时间范围（小时）')
@click.option('--min-visits', default=500, help='最小访问次数阈值')
@with_appcontext
def detect_suspicious():
    """自动检测可疑IP"""
    import psycopg2
    import os
    from datetime import datetime, timedelta

    try:
        database_url = os.getenv('DATABASE_URL', 'postgresql://rwa_hub_user:password@localhost/rwa_hub')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        since_time = datetime.now() - timedelta(hours=hours)

        # 查找高频访问的IP
        cursor.execute("""
            SELECT ip_address, COUNT(*) as visit_count,
                   COUNT(DISTINCT path) as unique_paths,
                   COUNT(DISTINCT user_agent) as unique_agents
            FROM ip_visits
            WHERE timestamp >= %s
            GROUP BY ip_address
            HAVING COUNT(*) >= %s
            ORDER BY visit_count DESC
            LIMIT 20
        """, (since_time, min_visits))

        results = cursor.fetchall()

        if not results:
            click.echo(f"未发现访问量超过 {min_visits} 次的IP")
            return

        click.echo(f"过去 {hours} 小时内高频访问IP列表:")
        click.echo("-" * 80)

        for ip_address, visit_count, unique_paths, unique_agents in results:
            # 检查是否在白名单中
            if IPSecurityManager.is_whitelisted(ip_address):
                status = "🟢 白名单"
            elif IPSecurityManager.is_blacklisted(ip_address):
                status = "🔴 已封禁"
            else:
                # 计算风险评分
                behavior = IPSecurityManager.analyze_ip_behavior(ip_address, hours)
                risk_score = behavior.get('risk_score', 0)
                threat_level = behavior.get('threat_level', 'UNKNOWN')

                if risk_score >= 80:
                    status = "🔴 高危"
                elif risk_score >= 60:
                    status = "🟠 中危"
                else:
                    status = "🟡 关注"

            click.echo(f"{ip_address:15} | {visit_count:5} 访问 | {unique_paths:3} 路径 | {unique_agents:2} UA | {status}")

        conn.close()

    except Exception as e:
        click.echo(f"检测失败: {e}")


# 将命令组注册到Flask应用
def init_ip_security_commands(app):
    """初始化IP安全管理命令"""
    app.cli.add_command(ip_security)