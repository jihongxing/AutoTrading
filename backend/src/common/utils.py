"""
BTC 自动交易系统 — 工具函数

提供 UTC 时间处理等通用工具。
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    获取当前 UTC 时间
    
    Returns:
        带时区信息的 UTC datetime
    """
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """
    将 datetime 转换为 UTC 时间
    
    Args:
        dt: 输入的 datetime（可带或不带时区）
    
    Returns:
        UTC 时间
    """
    if dt.tzinfo is None:
        # 假设无时区的时间为 UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def from_utc_ms(ts_ms: int) -> datetime:
    """
    将 UTC 毫秒时间戳转换为 datetime
    
    Args:
        ts_ms: UTC 毫秒时间戳
    
    Returns:
        带时区信息的 UTC datetime
    """
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def to_utc_ms(dt: datetime) -> int:
    """
    将 datetime 转换为 UTC 毫秒时间戳
    
    Args:
        dt: 输入的 datetime
    
    Returns:
        UTC 毫秒时间戳
    """
    utc_dt = to_utc(dt)
    return int(utc_dt.timestamp() * 1000)


def generate_order_id(prefix: str = "ORD") -> str:
    """
    生成唯一订单 ID
    
    Args:
        prefix: 订单 ID 前缀
    
    Returns:
        唯一订单 ID，格式: {prefix}_{timestamp}_{random}
    """
    import uuid
    ts = int(utc_now().timestamp() * 1000)
    rand = uuid.uuid4().hex[:8]
    return f"{prefix}_{ts}_{rand}"
