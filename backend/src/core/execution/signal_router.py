"""
BTC 自动交易系统 — 信号路由器

将策略信号路由到多用户执行器。
"""

import uuid
from typing import Any

from src.common.logging import get_logger
from src.common.models import Claim
from src.common.utils import utc_now
from src.user.context import TradingSignal

from .multi_executor import BroadcastResult, MultiUserExecutor

logger = get_logger(__name__)


class SignalRouter:
    """
    信号路由器
    
    将策略层产出的 Claim 转换为 TradingSignal，
    并路由到多用户执行器。
    """
    
    def __init__(self, executor: MultiUserExecutor):
        self.executor = executor
        
        # 默认配置
        self._default_symbol = "BTCUSDT"
        self._default_position_pct = 0.02
        self._min_confidence = 0.6
    
    async def route_claims(
        self,
        claims: list[Claim],
        aggregated_confidence: float,
        direction: str,
    ) -> BroadcastResult | None:
        """
        路由 Claim 列表
        
        Args:
            claims: Claim 列表
            aggregated_confidence: 聚合置信度
            direction: 方向 ("long" / "short")
        
        Returns:
            广播结果，如果不满足条件则返回 None
        """
        # 检查置信度
        if aggregated_confidence < self._min_confidence:
            logger.debug(f"置信度不足: {aggregated_confidence:.2f} < {self._min_confidence}")
            return None
        
        # 创建交易信号
        signal = TradingSignal(
            signal_id=str(uuid.uuid4())[:8],
            symbol=self._default_symbol,
            direction=direction,
            confidence=aggregated_confidence,
            position_pct=self._calculate_position_pct(aggregated_confidence),
            source_claims=claims,
        )
        
        logger.info(
            f"路由信号: {signal.signal_id}, direction={direction}, "
            f"confidence={aggregated_confidence:.2f}, position={signal.position_pct:.2%}"
        )
        
        # 广播给所有用户
        return await self.executor.broadcast_signal(signal)
    
    async def route_signal(self, signal: TradingSignal) -> BroadcastResult:
        """
        直接路由信号
        
        Args:
            signal: 交易信号
        
        Returns:
            广播结果
        """
        return await self.executor.broadcast_signal(signal)
    
    def _calculate_position_pct(self, confidence: float) -> float:
        """
        根据置信度计算仓位比例
        
        置信度越高，仓位越大（但不超过默认值的 2 倍）
        """
        # 基础仓位
        base = self._default_position_pct
        
        # 置信度加成（0.6-1.0 映射到 1.0-2.0）
        multiplier = 1.0 + (confidence - 0.6) / 0.4
        multiplier = min(multiplier, 2.0)
        
        return base * multiplier
    
    def set_default_symbol(self, symbol: str) -> None:
        """设置默认交易对"""
        self._default_symbol = symbol
    
    def set_default_position_pct(self, pct: float) -> None:
        """设置默认仓位比例"""
        self._default_position_pct = pct
    
    def set_min_confidence(self, confidence: float) -> None:
        """设置最小置信度"""
        self._min_confidence = confidence
