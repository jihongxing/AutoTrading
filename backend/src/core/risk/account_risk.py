"""
BTC 自动交易系统 — 账户生存性风控

监控回撤、单日亏损、连续亏损等账户级风险。
"""

from src.common.enums import RiskEventType, RiskLevel
from src.common.logging import get_logger
from src.common.models import RiskCheckResult, RiskEvent

from .base import RiskChecker, RiskContext
from .constants import RiskThresholds

logger = get_logger(__name__)


class AccountRiskChecker(RiskChecker):
    """
    账户生存性风控检查器
    
    检查项：
    - 最大回撤
    - 单日最大亏损
    - 连续亏损次数
    - 周最大亏损
    """
    
    @property
    def name(self) -> str:
        return "account_risk"
    
    def __init__(
        self,
        max_drawdown: float | None = None,
        daily_max_loss: float | None = None,
        weekly_max_loss: float | None = None,
        consecutive_loss_cooldown: int | None = None,
    ):
        self.max_drawdown = max_drawdown or RiskThresholds.account.max_drawdown
        self.daily_max_loss = daily_max_loss or RiskThresholds.account.daily_max_loss
        self.weekly_max_loss = weekly_max_loss or RiskThresholds.account.weekly_max_loss
        self.consecutive_loss_cooldown = (
            consecutive_loss_cooldown or RiskThresholds.account.consecutive_loss_cooldown
        )
    
    async def check(self, context: RiskContext) -> RiskCheckResult:
        """执行账户风控检查"""
        events: list[RiskEvent] = []
        
        # 检查最大回撤
        if context.drawdown >= self.max_drawdown:
            event = self._create_event(
                event_type=RiskEventType.DRAWDOWN_EXCEEDED.value,
                level=RiskLevel.RISK_LOCKED,
                description=f"回撤 {context.drawdown:.2%} 超过阈值 {self.max_drawdown:.2%}",
                value=context.drawdown,
                threshold=self.max_drawdown,
            )
            events.append(event)
            logger.warning(f"回撤超限: {context.drawdown:.2%}")
            return self._reject(
                level=RiskLevel.RISK_LOCKED,
                reason="回撤超过最大阈值",
                events=events,
            )
        
        # 检查单日亏损
        daily_loss_ratio = context.daily_loss_ratio
        if daily_loss_ratio >= self.daily_max_loss:
            event = self._create_event(
                event_type=RiskEventType.DAILY_LOSS_EXCEEDED.value,
                level=RiskLevel.COOLDOWN,
                description=f"单日亏损 {daily_loss_ratio:.2%} 超过阈值 {self.daily_max_loss:.2%}",
                value=daily_loss_ratio,
                threshold=self.daily_max_loss,
            )
            events.append(event)
            logger.warning(f"单日亏损超限: {daily_loss_ratio:.2%}")
            return self._reject(
                level=RiskLevel.COOLDOWN,
                reason="单日亏损超过阈值",
                events=events,
            )
        
        # 检查连续亏损
        if context.consecutive_losses >= self.consecutive_loss_cooldown:
            event = self._create_event(
                event_type=RiskEventType.CONSECUTIVE_LOSS.value,
                level=RiskLevel.COOLDOWN,
                description=f"连续亏损 {context.consecutive_losses} 次",
                value=float(context.consecutive_losses),
                threshold=float(self.consecutive_loss_cooldown),
            )
            events.append(event)
            logger.warning(f"连续亏损: {context.consecutive_losses} 次")
            return self._reject(
                level=RiskLevel.COOLDOWN,
                reason="连续亏损次数过多",
                events=events,
            )
        
        # 检查周亏损
        if context.equity > 0:
            weekly_loss_ratio = -context.weekly_pnl / context.equity if context.weekly_pnl < 0 else 0
            if weekly_loss_ratio >= self.weekly_max_loss:
                event = self._create_event(
                    event_type=RiskEventType.DAILY_LOSS_EXCEEDED.value,
                    level=RiskLevel.COOLDOWN,
                    description=f"周亏损 {weekly_loss_ratio:.2%} 超过阈值 {self.weekly_max_loss:.2%}",
                    value=weekly_loss_ratio,
                    threshold=self.weekly_max_loss,
                )
                events.append(event)
                return self._reject(
                    level=RiskLevel.COOLDOWN,
                    reason="周亏损超过阈值",
                    events=events,
                )
        
        # 检查预警
        if context.drawdown >= self.max_drawdown * 0.8:
            return self._approve(level=RiskLevel.WARNING)
        
        return self._approve()
