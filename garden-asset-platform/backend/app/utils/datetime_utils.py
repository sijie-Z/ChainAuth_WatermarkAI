"""
日期时间工具函数
"""
from datetime import datetime, timedelta
from typing import Optional


def format_datetime(dt: Optional[datetime], fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化日期时间"""
    if dt is None:
        return ''
    return dt.strftime(fmt)


def format_date(dt: Optional[datetime], fmt: str = '%Y-%m-%d') -> str:
    """格式化日期"""
    return format_datetime(dt, fmt)


def parse_datetime(dt_str: str, fmt: str = '%Y-%m-%d %H:%M:%S') -> Optional[datetime]:
    """解析日期时间字符串"""
    try:
        return datetime.strptime(dt_str, fmt)
    except (ValueError, TypeError):
        return None


def get_duration_months(start: datetime, end: datetime) -> int:
    """计算月数差"""
    return (end.year - start.year) * 12 + (end.month - start.month)


def add_months(dt: datetime, months: int) -> datetime:
    """添加月数"""
    month = dt.month + months
    year = dt.year + month // 12
    month = month % 12
    if month == 0:
        month = 12
        year -= 1

    # 处理日期溢出
    day = min(dt.day, 28)
    return dt.replace(year=year, month=month, day=day)


def is_expired(expiry_date: Optional[datetime]) -> bool:
    """检查是否已过期"""
    if expiry_date is None:
        return False
    return datetime.utcnow() > expiry_date


def get_remaining_days(expiry_date: Optional[datetime]) -> int:
    """获取剩余天数"""
    if expiry_date is None:
        return -1  # 永久有效
    delta = expiry_date - datetime.utcnow()
    return max(0, delta.days)
