from datetime import datetime, timedelta
from sqlalchemy import func, text
from app.models import IPVisit
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

class IPStatsService:
    """IP访问统计服务"""
    
    @staticmethod
    def get_hourly_stats(date=None):
        """获取24小时内每小时的访问统计"""
        if date is None:
            date = datetime.utcnow().date()
        
        start_time = datetime.combine(date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        # 查询每小时的访问次数
        query = db.session.query(
            func.extract('hour', IPVisit.timestamp).label('hour'),
            func.count(IPVisit.id).label('visit_count'),
            func.count(func.distinct(IPVisit.ip_address)).label('unique_ips')
        ).filter(
            IPVisit.timestamp >= start_time,
            IPVisit.timestamp < end_time
        ).group_by(
            func.extract('hour', IPVisit.timestamp)
        ).order_by('hour')
        
        results = query.all()
        
        # 构建24小时完整数据（0-23小时）
        hourly_data = {int(r.hour): {'visits': r.visit_count, 'unique_ips': r.unique_ips} for r in results}
        
        labels = [f"{i:02d}:00" for i in range(24)]
        visit_data = [hourly_data.get(i, {'visits': 0, 'unique_ips': 0})['visits'] for i in range(24)]
        unique_ip_data = [hourly_data.get(i, {'visits': 0, 'unique_ips': 0})['unique_ips'] for i in range(24)]
        
        # 计算总计
        total_visits = sum(visit_data)
        total_unique_ips = IPStatsService._get_unique_ips_count(start_time, end_time)
        
        return {
            'labels': labels,
            'visit_data': visit_data,
            'unique_ip_data': unique_ip_data,
            'total_visits': total_visits,
            'total_unique_ips': total_unique_ips,
            'period': f"{date.strftime('%Y-%m-%d')} 24小时统计"
        }
    
    @staticmethod
    def get_daily_stats(days=7):
        """获取最近N天每天的访问统计"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # 查询每天的访问次数
        query = db.session.query(
            func.date(IPVisit.timestamp).label('visit_date'),
            func.count(IPVisit.id).label('visit_count'),
            func.count(func.distinct(IPVisit.ip_address)).label('unique_ips')
        ).filter(
            IPVisit.timestamp >= start_time,
            IPVisit.timestamp <= end_time
        ).group_by(
            func.date(IPVisit.timestamp)
        ).order_by('visit_date')
        
        results = query.all()
        
        # 构建完整日期数据
        daily_data = {r.visit_date: {'visits': r.visit_count, 'unique_ips': r.unique_ips} for r in results}
        
        labels = []
        visit_data = []
        unique_ip_data = []
        
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%m-%d'))
            data = daily_data.get(current_date, {'visits': 0, 'unique_ips': 0})
            visit_data.append(data['visits'])
            unique_ip_data.append(data['unique_ips'])
            current_date += timedelta(days=1)
        
        # 计算总计
        total_visits = sum(visit_data)
        total_unique_ips = IPStatsService._get_unique_ips_count(start_time, end_time)
        
        return {
            'labels': labels,
            'visit_data': visit_data,
            'unique_ip_data': unique_ip_data,
            'total_visits': total_visits,
            'total_unique_ips': total_unique_ips,
            'period': f"最近{days}天统计"
        }
    
    @staticmethod
    def get_monthly_stats(months=12):
        """获取最近N个月每月的访问统计"""
        end_date = datetime.utcnow().date()
        start_date = end_date.replace(day=1) - timedelta(days=(months-1)*31)  # 粗略计算
        start_date = start_date.replace(day=1)  # 月初
        
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # 查询每月的访问次数
        query = db.session.query(
            func.extract('year', IPVisit.timestamp).label('year'),
            func.extract('month', IPVisit.timestamp).label('month'),
            func.count(IPVisit.id).label('visit_count'),
            func.count(func.distinct(IPVisit.ip_address)).label('unique_ips')
        ).filter(
            IPVisit.timestamp >= start_time,
            IPVisit.timestamp <= end_time
        ).group_by(
            func.extract('year', IPVisit.timestamp),
            func.extract('month', IPVisit.timestamp)
        ).order_by('year', 'month')
        
        results = query.all()
        
        # 构建月度数据
        monthly_data = {}
        for r in results:
            key = f"{int(r.year)}-{int(r.month):02d}"
            monthly_data[key] = {'visits': r.visit_count, 'unique_ips': r.unique_ips}
        
        labels = []
        visit_data = []
        unique_ip_data = []
        
        # 生成最近N个月的标签
        current_date = start_date
        while current_date <= end_date:
            month_key = current_date.strftime('%Y-%m')
            labels.append(current_date.strftime('%Y-%m'))
            data = monthly_data.get(month_key, {'visits': 0, 'unique_ips': 0})
            visit_data.append(data['visits'])
            unique_ip_data.append(data['unique_ips'])
            
            # 下个月
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # 计算总计
        total_visits = sum(visit_data)
        total_unique_ips = IPStatsService._get_unique_ips_count(start_time, end_time)
        
        return {
            'labels': labels,
            'visit_data': visit_data,
            'unique_ip_data': unique_ip_data,
            'total_visits': total_visits,
            'total_unique_ips': total_unique_ips,
            'period': f"最近{months}个月统计"
        }
    
    @staticmethod
    def get_all_time_stats():
        """获取全部时间的访问统计（按周或月分组）"""
        # 获取第一条和最后一条记录的时间
        first_visit = db.session.query(func.min(IPVisit.timestamp)).scalar()
        last_visit = db.session.query(func.max(IPVisit.timestamp)).scalar()
        
        if not first_visit:
            return {
                'labels': [],
                'visit_data': [],
                'unique_ip_data': [],
                'total_visits': 0,
                'total_unique_ips': 0,
                'period': "暂无数据"
            }
        
        # 计算时间跨度
        time_span = (last_visit - first_visit).days
        
        if time_span <= 30:
            # 30天内按天分组
            return IPStatsService._get_all_time_daily_stats(first_visit, last_visit)
        elif time_span <= 365:
            # 一年内按周分组
            return IPStatsService._get_all_time_weekly_stats(first_visit, last_visit)
        else:
            # 超过一年按月分组
            return IPStatsService._get_all_time_monthly_stats(first_visit, last_visit)
    
    @staticmethod
    def _get_all_time_daily_stats(start_time, end_time):
        """全部时间按天统计"""
        query = db.session.query(
            func.date(IPVisit.timestamp).label('visit_date'),
            func.count(IPVisit.id).label('visit_count'),
            func.count(func.distinct(IPVisit.ip_address)).label('unique_ips')
        ).filter(
            IPVisit.timestamp >= start_time,
            IPVisit.timestamp <= end_time
        ).group_by(
            func.date(IPVisit.timestamp)
        ).order_by('visit_date')
        
        results = query.all()
        
        labels = [r.visit_date.strftime('%m-%d') for r in results]
        visit_data = [r.visit_count for r in results]
        unique_ip_data = [r.unique_ips for r in results]
        
        total_visits = sum(visit_data)
        total_unique_ips = IPStatsService._get_unique_ips_count(start_time, end_time)
        
        return {
            'labels': labels,
            'visit_data': visit_data,
            'unique_ip_data': unique_ip_data,
            'total_visits': total_visits,
            'total_unique_ips': total_unique_ips,
            'period': "全部时间统计（按天）"
        }
    
    @staticmethod
    def _get_all_time_weekly_stats(start_time, end_time):
        """全部时间按周统计"""
        # 使用PostgreSQL的date_trunc函数按周分组
        query = db.session.query(
            func.date_trunc('week', IPVisit.timestamp).label('week_start'),
            func.count(IPVisit.id).label('visit_count'),
            func.count(func.distinct(IPVisit.ip_address)).label('unique_ips')
        ).filter(
            IPVisit.timestamp >= start_time,
            IPVisit.timestamp <= end_time
        ).group_by(
            func.date_trunc('week', IPVisit.timestamp)
        ).order_by('week_start')
        
        results = query.all()
        
        labels = [r.week_start.strftime('%m-%d') for r in results]
        visit_data = [r.visit_count for r in results]
        unique_ip_data = [r.unique_ips for r in results]
        
        total_visits = sum(visit_data)
        total_unique_ips = IPStatsService._get_unique_ips_count(start_time, end_time)
        
        return {
            'labels': labels,
            'visit_data': visit_data,
            'unique_ip_data': unique_ip_data,
            'total_visits': total_visits,
            'total_unique_ips': total_unique_ips,
            'period': "全部时间统计（按周）"
        }
    
    @staticmethod
    def _get_all_time_monthly_stats(start_time, end_time):
        """全部时间按月统计"""
        query = db.session.query(
            func.date_trunc('month', IPVisit.timestamp).label('month_start'),
            func.count(IPVisit.id).label('visit_count'),
            func.count(func.distinct(IPVisit.ip_address)).label('unique_ips')
        ).filter(
            IPVisit.timestamp >= start_time,
            IPVisit.timestamp <= end_time
        ).group_by(
            func.date_trunc('month', IPVisit.timestamp)
        ).order_by('month_start')
        
        results = query.all()
        
        labels = [r.month_start.strftime('%Y-%m') for r in results]
        visit_data = [r.visit_count for r in results]
        unique_ip_data = [r.unique_ips for r in results]
        
        total_visits = sum(visit_data)
        total_unique_ips = IPStatsService._get_unique_ips_count(start_time, end_time)
        
        return {
            'labels': labels,
            'visit_data': visit_data,
            'unique_ip_data': unique_ip_data,
            'total_visits': total_visits,
            'total_unique_ips': total_unique_ips,
            'period': "全部时间统计（按月）"
        }
    
    @staticmethod
    def _get_unique_ips_count(start_time, end_time):
        """获取指定时间范围内的独立IP数量"""
        return db.session.query(
            func.count(func.distinct(IPVisit.ip_address))
        ).filter(
            IPVisit.timestamp >= start_time,
            IPVisit.timestamp <= end_time
        ).scalar() or 0
    
    @staticmethod
    def get_summary_stats():
        """获取总体统计信息"""
        total_visits = db.session.query(func.count(IPVisit.id)).scalar() or 0
        total_unique_ips = db.session.query(func.count(func.distinct(IPVisit.ip_address))).scalar() or 0
        
        # 今日统计
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_visits = db.session.query(func.count(IPVisit.id)).filter(
            IPVisit.timestamp >= today_start,
            IPVisit.timestamp <= today_end
        ).scalar() or 0
        
        today_unique_ips = db.session.query(func.count(func.distinct(IPVisit.ip_address))).filter(
            IPVisit.timestamp >= today_start,
            IPVisit.timestamp <= today_end
        ).scalar() or 0
        
        # 昨日统计
        yesterday = today - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())
        
        yesterday_visits = db.session.query(func.count(IPVisit.id)).filter(
            IPVisit.timestamp >= yesterday_start,
            IPVisit.timestamp <= yesterday_end
        ).scalar() or 0
        
        return {
            'total_visits': total_visits,
            'total_unique_ips': total_unique_ips,
            'today_visits': today_visits,
            'today_unique_ips': today_unique_ips,
            'yesterday_visits': yesterday_visits,
            'growth_rate': ((today_visits - yesterday_visits) / max(yesterday_visits, 1)) * 100 if yesterday_visits > 0 else 0
        } 