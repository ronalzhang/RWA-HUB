"""
datetime兼容性模块 - 提供Python 3.12+兼容的函数

在Python 3.12中，datetime.utcnow()被移除，推荐使用datetime.now(timezone.utc)
这个模块提供了兼容函数用于替代datetime.utcnow()
"""

from datetime import datetime, timezone, timedelta, date

def get_utc_now():
    """
    获取当前UTC时间，兼容Python 3.12+
    
    注意：此函数返回无时区的datetime对象，与原datetime.utcnow()行为一致
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

def get_utc_today():
    """
    获取当前UTC日期，兼容Python 3.12+
    """
    return get_utc_now().date()

def get_utc_datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0):
    """
    创建指定的UTC datetime对象，兼容Python 3.12+
    """
    dt = datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)
    return dt.replace(tzinfo=None)  # 移除时区信息以保持与旧代码兼容 