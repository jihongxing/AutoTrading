"""
BTC 自动交易系统 — 执行完整性风控

监控滑点、成交率、延迟等执行质量指标。
"""

from src.common.enums import RiskEventType, RiskLevel
from src.common.logging import get_logger
from src.common.models import RiskCheckResult, RiskEvent

from .base import RiskChecker, RiskContext
from .constants import RiskThresholds

logger = get_logger(__name__)


class ExecutionRiskChecker(RiskChecker):
    """
    执行完整性风控检查器
    
    检查项：
    - 滑点分布
    - 成交率
    - 撮合延迟
    """
    
    @property
    def name(self) -> str:
        return "execution_risk"
    
    def __init__(
        self,
        max_slippage: float | None = None,
        min_fill_rate: float | None = None,
        max_latency_ms: int | None = None,
    ):
        self.max_slippage = max_slippage or RiskThresholds.execution.max_slippage
        self.min_fill_rate = min_fill_rate or RiskThresholds.execution.min_fill_rate
        self.max_latency_ms = max_latency_ms or RiskThresholds.execution.max_latency_ms
    
    async def check(self, context: RiskContext) -> RiskCheckResult:
        """执行风控检查"""
        events: list[RiskEvent] = []
        
        # 检查滑点
        if context.recent_slippages:
            avg_slippage = sum(context.recent_slippages) / len(context.recent_slippages)
            if avg_slippage > self.max_slippage:
                event = self._create_event(
                    event_type=RiskEventType.EXECUTION_FAILURE.value,
                    level=RiskLevel.WARNING,
                    description=f"平均滑点 {avg_slippage:.4%} 超过阈值 {self.max_slippage:.4%}",
                    value=avg_slippage,
                    threshold=self.max_slippage,
                )
                events.append(event)
                logger.warning(f"滑点过高: {avg_slippage:.4%}")
                
                # 滑点严重时拒绝
                if avg_slippage > self.max_slippage * 2:
                    return self._reject(
                        level=RiskLevel.COOLDOWN,
                        reason="滑点严重超标",
                        events=events,
                    )
        
        # 检查成交率
        if context.recent_fill_rates:
            avg_fill_rate = sum(context.recent_fill_rates) / len(context.recent_fill_rates)
            if avg_fill_rate < self.min_fill_rate:
                event = self._create_event(
                    event_type=RiskEventType.EXECUTION_FAILURE.value,
                    level=RiskLevel.WARNING,
                    description=f"成交率 {avg_fill_rate:.2%} 低于阈值 {self.min_fill_rate:.2%}",
                    value=avg_fill_rate,
                    threshold=self.min_fill_rate,
                )
                events.append(event)
                logger.warning(f"成交率过低: {avg_fill_rate:.2%}")
        
        # 检查延迟
        if context.recent_latencies:
            avg_latency = sum(context.recent_latencies) / len(context.recent_latencies)
            if avg_latency > self.max_latency_ms:
                event = self._create_event(
                    event_type=RiskEventType.EXECUTION_FAILURE.value,
                    level=RiskLevel.WARNING,
                    description=f"平均延迟 {avg_latency}ms 超过阈值 {self.max_latency_ms}ms",
                    value=avg_latency,
                    threshold=float(self.max_latency_ms),
                )
                events.append(event)
                logger.warning(f"延迟过高: {avg_latency}ms")
        
        # 有警告但不拒绝
        if events:
            return RiskCheckResult(
                approved=True,
                level=RiskLevel.WARNING,
                events=events,
            )
        
        return self._approve()
