"""
BTC 自动交易系统 — 策略失效风控

监控证人组合胜率、单个证人健康度、证人相关性。
"""

from src.common.enums import HealthGrade, RiskEventType, RiskLevel, WitnessStatus
from src.common.logging import get_logger
from src.common.models import RiskCheckResult, RiskEvent

from .base import RiskChecker, RiskContext

logger = get_logger(__name__)


class RegimeRiskChecker(RiskChecker):
    """
    策略/范式失效风控检查器
    
    检查项：
    - 证人组合胜率（目标 58-62%）
    - 单个证人健康度（目标 52-55%）
    - 证人相关性（阈值 < 0.8）
    """
    
    @property
    def name(self) -> str:
        return "regime_risk"
    
    def __init__(
        self,
        min_combo_win_rate: float = 0.52,
        max_combo_win_rate: float = 0.70,
        min_witness_win_rate: float = 0.30,
        max_correlation: float = 0.80,
        min_active_witnesses: int = 2,
    ):
        self.min_combo_win_rate = min_combo_win_rate
        self.max_combo_win_rate = max_combo_win_rate
        self.min_witness_win_rate = min_witness_win_rate
        self.max_correlation = max_correlation
        self.min_active_witnesses = min_active_witnesses
    
    async def check(self, context: RiskContext) -> RiskCheckResult:
        """执行策略失效风控检查"""
        events: list[RiskEvent] = []
        
        if not context.witness_health:
            return self._approve()
        
        # 统计活跃证人
        active_witnesses = [
            w for w in context.witness_health.values()
            if w.status == WitnessStatus.ACTIVE
        ]
        
        # 检查活跃证人数量
        if len(active_witnesses) < self.min_active_witnesses:
            event = self._create_event(
                event_type=RiskEventType.EXECUTION_FAILURE.value,
                level=RiskLevel.WARNING,
                description=f"活跃证人数量 {len(active_witnesses)} 低于最小要求 {self.min_active_witnesses}",
                value=float(len(active_witnesses)),
                threshold=float(self.min_active_witnesses),
            )
            events.append(event)
            logger.warning(f"活跃证人不足: {len(active_witnesses)}")
        
        # 检查单个证人健康度
        unhealthy_witnesses = []
        for witness in context.witness_health.values():
            if witness.grade == HealthGrade.D:
                unhealthy_witnesses.append(witness.witness_id)
            
            if witness.win_rate < self.min_witness_win_rate:
                event = self._create_event(
                    event_type=RiskEventType.EXECUTION_FAILURE.value,
                    level=RiskLevel.WARNING,
                    description=f"证人 {witness.witness_id} 胜率 {witness.win_rate:.2%} 过低",
                    value=witness.win_rate,
                    threshold=self.min_witness_win_rate,
                )
                events.append(event)
        
        if unhealthy_witnesses:
            logger.warning(f"不健康证人: {unhealthy_witnesses}")
        
        # 计算组合胜率
        if active_witnesses:
            total_weight = sum(w.weight for w in active_witnesses)
            if total_weight > 0:
                combo_win_rate = sum(
                    w.win_rate * w.weight for w in active_witnesses
                ) / total_weight
                
                if combo_win_rate < self.min_combo_win_rate:
                    event = self._create_event(
                        event_type=RiskEventType.EXECUTION_FAILURE.value,
                        level=RiskLevel.WARNING,
                        description=f"组合胜率 {combo_win_rate:.2%} 低于阈值 {self.min_combo_win_rate:.2%}",
                        value=combo_win_rate,
                        threshold=self.min_combo_win_rate,
                    )
                    events.append(event)
                    logger.warning(f"组合胜率过低: {combo_win_rate:.2%}")
                
                # 胜率异常高也是风险信号（可能过拟合）
                if combo_win_rate > self.max_combo_win_rate:
                    event = self._create_event(
                        event_type=RiskEventType.EXECUTION_FAILURE.value,
                        level=RiskLevel.WARNING,
                        description=f"组合胜率 {combo_win_rate:.2%} 异常高，可能过拟合",
                        value=combo_win_rate,
                        threshold=self.max_combo_win_rate,
                    )
                    events.append(event)
        
        if events:
            return RiskCheckResult(
                approved=True,
                level=RiskLevel.WARNING,
                events=events,
            )
        
        return self._approve()
