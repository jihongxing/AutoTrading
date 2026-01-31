"""
BTC 自动交易系统 — 时段指标

交易时段识别。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.common.utils import utc_now


class SessionType(str, Enum):
    """时段类型"""
    ASIA_OPEN = "asia_open"
    ASIA_CLOSE = "asia_close"
    EUROPE_OPEN = "europe_open"
    EUROPE_CLOSE = "europe_close"
    US_OPEN = "us_open"
    US_CLOSE = "us_close"
    LOW_LIQUIDITY = "low_liquidity"
    NORMAL = "normal"


@dataclass
class SessionInfo:
    """时段信息"""
    session: SessionType
    is_high_volatility: bool
    is_low_liquidity: bool
    is_weekend: bool
    hour: int
    weekday: int
    volatility_factor: float
    liquidity_factor: float


# 时段定义（UTC）
SESSION_HOURS = {
    SessionType.ASIA_OPEN: (0, 2),
    SessionType.ASIA_CLOSE: (6, 8),
    SessionType.EUROPE_OPEN: (7, 9),
    SessionType.EUROPE_CLOSE: (15, 17),
    SessionType.US_OPEN: (13, 16),
    SessionType.US_CLOSE: (20, 22),
    SessionType.LOW_LIQUIDITY: [(4, 6), (21, 23)],
}

# 高波动时段
HIGH_VOLATILITY_SESSIONS = {
    SessionType.ASIA_OPEN,
    SessionType.EUROPE_OPEN,
    SessionType.US_OPEN,
}

# 低流动性时段
LOW_LIQUIDITY_SESSIONS = {
    SessionType.LOW_LIQUIDITY,
}


def get_session_info(timestamp: datetime | None = None) -> SessionInfo:
    """
    获取时段信息
    
    Args:
        timestamp: 时间戳（默认当前时间）
    
    Returns:
        时段信息
    """
    if timestamp is None:
        timestamp = utc_now()
    
    hour = timestamp.hour
    weekday = timestamp.weekday()
    is_weekend = weekday >= 5
    
    # 识别当前时段
    session = _identify_session(hour)
    
    # 计算波动率和流动性因子
    is_high_volatility = session in HIGH_VOLATILITY_SESSIONS
    is_low_liquidity = session in LOW_LIQUIDITY_SESSIONS or is_weekend
    
    volatility_factor = 1.2 if is_high_volatility else 1.0
    liquidity_factor = 0.7 if is_low_liquidity else 1.0
    
    if is_weekend:
        volatility_factor *= 0.8
        liquidity_factor *= 0.6
    
    return SessionInfo(
        session=session,
        is_high_volatility=is_high_volatility,
        is_low_liquidity=is_low_liquidity,
        is_weekend=is_weekend,
        hour=hour,
        weekday=weekday,
        volatility_factor=volatility_factor,
        liquidity_factor=liquidity_factor,
    )


def _identify_session(hour: int) -> SessionType:
    """识别时段"""
    # 检查低流动性时段
    low_liq_ranges = SESSION_HOURS[SessionType.LOW_LIQUIDITY]
    for start, end in low_liq_ranges:
        if start <= hour < end:
            return SessionType.LOW_LIQUIDITY
    
    # 检查其他时段
    for session, (start, end) in SESSION_HOURS.items():
        if session == SessionType.LOW_LIQUIDITY:
            continue
        if start <= hour < end:
            return session
    
    return SessionType.NORMAL


def is_trading_favorable(timestamp: datetime | None = None) -> bool:
    """
    判断当前时段是否适合交易
    
    Args:
        timestamp: 时间戳
    
    Returns:
        是否适合交易
    """
    info = get_session_info(timestamp)
    
    # 周末不适合
    if info.is_weekend:
        return False
    
    # 低流动性时段不适合
    if info.is_low_liquidity:
        return False
    
    return True
