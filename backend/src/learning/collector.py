"""
BTC 自动交易系统 — 学习数据收集器

收集用于自学习的交易、信号和市场数据。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

from .constants import VALID_LEARNING_STATES

logger = get_logger(__name__)


@dataclass
class TradeData:
    """交易数据"""
    trade_id: str
    timestamp: datetime
    symbol: str
    direction: str
    entry_price: float
    exit_price: float | None
    quantity: float
    pnl: float
    is_win: bool
    witness_ids: list[str]
    state_at_entry: str
    duration_seconds: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalData:
    """信号数据"""
    signal_id: str
    timestamp: datetime
    witness_id: str
    claim_type: str
    confidence: float
    direction: str | None
    was_executed: bool
    result: str | None  # win/loss/pending
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketSnapshot:
    """市场快照"""
    timestamp: datetime
    price: float
    volume_24h: float
    volatility: float
    trend: str  # up/down/sideways
    metadata: dict[str, Any] = field(default_factory=dict)


class LearningDataCollector:
    """
    学习数据收集器
    
    收集用于自学习的各类数据：
    - 交易数据
    - 信号数据
    - 市场数据
    """
    
    def __init__(self):
        self._trade_data: list[TradeData] = []
        self._signal_data: list[SignalData] = []
        self._market_snapshots: list[MarketSnapshot] = []
    
    async def collect_trade_data(
        self,
        start: datetime,
        end: datetime,
    ) -> list[TradeData]:
        """
        收集交易数据
        
        Args:
            start: 开始时间
            end: 结束时间
        
        Returns:
            交易数据列表
        """
        # 过滤时间范围和有效状态
        # 处理 naive/aware datetime 兼容性
        result = []
        for t in self._trade_data:
            if t.state_at_entry not in VALID_LEARNING_STATES:
                continue
            # 转换为 naive 比较
            ts = t.timestamp.replace(tzinfo=None) if t.timestamp.tzinfo else t.timestamp
            s = start.replace(tzinfo=None) if start.tzinfo else start
            e = end.replace(tzinfo=None) if end.tzinfo else end
            if s <= ts <= e:
                result.append(t)
        
        logger.info(
            f"收集交易数据: {len(result)} 条",
            extra={"start": start.isoformat(), "end": end.isoformat(), "count": len(result)},
        )
        
        return result
    
    async def collect_signal_data(
        self,
        start: datetime,
        end: datetime,
    ) -> list[SignalData]:
        """
        收集信号数据
        
        Args:
            start: 开始时间
            end: 结束时间
        
        Returns:
            信号数据列表
        """
        # 处理 naive/aware datetime 兼容性
        result = []
        for sig in self._signal_data:
            ts = sig.timestamp.replace(tzinfo=None) if sig.timestamp.tzinfo else sig.timestamp
            s = start.replace(tzinfo=None) if start.tzinfo else start
            e = end.replace(tzinfo=None) if end.tzinfo else end
            if s <= ts <= e:
                result.append(sig)
        
        logger.info(
            f"收集信号数据: {len(result)} 条",
            extra={"start": start.isoformat(), "end": end.isoformat(), "count": len(result)},
        )
        
        return result
    
    async def collect_market_data(
        self,
        start: datetime,
        end: datetime,
    ) -> list[MarketSnapshot]:
        """
        收集市场数据
        
        Args:
            start: 开始时间
            end: 结束时间
        
        Returns:
            市场快照列表
        """
        result = [
            m for m in self._market_snapshots
            if start <= m.timestamp <= end
        ]
        
        return result
    
    def record_trade(self, trade: TradeData) -> None:
        """记录交易数据"""
        self._trade_data.append(trade)
        logger.debug(f"记录交易: {trade.trade_id}")
    
    def record_signal(self, signal: SignalData) -> None:
        """记录信号数据"""
        self._signal_data.append(signal)
        logger.debug(f"记录信号: {signal.signal_id}")
    
    def record_market_snapshot(self, snapshot: MarketSnapshot) -> None:
        """记录市场快照"""
        self._market_snapshots.append(snapshot)
    
    def get_witness_trades(self, witness_id: str) -> list[TradeData]:
        """获取指定证人的交易数据"""
        return [t for t in self._trade_data if witness_id in t.witness_ids]
    
    def get_witness_signals(self, witness_id: str) -> list[SignalData]:
        """获取指定证人的信号数据"""
        return [s for s in self._signal_data if s.witness_id == witness_id]
    
    def clear_old_data(self, before: datetime) -> int:
        """清理旧数据"""
        original_count = len(self._trade_data) + len(self._signal_data)
        
        self._trade_data = [t for t in self._trade_data if t.timestamp >= before]
        self._signal_data = [s for s in self._signal_data if s.timestamp >= before]
        self._market_snapshots = [m for m in self._market_snapshots if m.timestamp >= before]
        
        new_count = len(self._trade_data) + len(self._signal_data)
        cleared = original_count - new_count
        
        logger.info(f"清理旧数据: {cleared} 条")
        return cleared
