"""
BTC 自动交易系统 — 恢复管理器

管理风控锁定后的恢复流程。
"""

from datetime import datetime, timedelta

from src.common.enums import RiskLevel
from src.common.logging import get_logger
from src.common.utils import utc_now

from .base import RiskContext
from .constants import RiskThresholds
from .engine import RiskControlEngine

logger = get_logger(__name__)


class RecoveryManager:
    """
    恢复管理器
    
    管理风控锁定后的解锁条件检查和降级运行。
    """
    
    def __init__(
        self,
        engine: RiskControlEngine,
        auto_unlock_hours: int | None = None,
        degraded_position_ratio: float | None = None,
    ):
        self.engine = engine
        self.auto_unlock_hours = auto_unlock_hours or RiskThresholds.recovery.auto_unlock_hours
        self.degraded_position_ratio = (
            degraded_position_ratio or RiskThresholds.recovery.degraded_position_ratio
        )
        self._degraded_mode = False
        self._recovery_start: datetime | None = None
    
    @property
    def is_degraded(self) -> bool:
        """是否处于降级模式"""
        return self._degraded_mode
    
    @property
    def position_limit_ratio(self) -> float:
        """当前仓位限制比例"""
        if self._degraded_mode:
            return self.degraded_position_ratio
        return 1.0
    
    async def check_auto_unlock(self) -> bool:
        """
        检查是否满足自动解锁条件
        
        Returns:
            是否可以自动解锁
        """
        if not self.engine.is_locked:
            return False
        
        if self.engine._lock_time is None:
            return False
        
        # 检查锁定时间
        elapsed = utc_now() - self.engine._lock_time
        if elapsed < timedelta(hours=self.auto_unlock_hours):
            remaining = timedelta(hours=self.auto_unlock_hours) - elapsed
            logger.info(f"自动解锁剩余时间: {remaining}")
            return False
        
        return True
    
    async def request_unlock(self, context: RiskContext) -> bool:
        """
        请求解锁
        
        Args:
            context: 当前风控上下文
        
        Returns:
            是否解锁成功
        """
        if not self.engine.is_locked:
            logger.info("系统未锁定，无需解锁")
            return True
        
        # 检查自动解锁条件
        if not await self.check_auto_unlock():
            logger.warning("未满足自动解锁条件")
            return False
        
        # 检查当前风险状态
        # 回撤必须恢复到安全水平
        if context.drawdown >= RiskThresholds.account.max_drawdown * 0.9:
            logger.warning(f"回撤仍然过高: {context.drawdown:.2%}")
            return False
        
        # 解锁成功，进入降级模式
        self.engine.reset_to_normal()
        self._degraded_mode = True
        self._recovery_start = utc_now()
        
        logger.info("系统解锁成功，进入降级运行模式")
        return True
    
    async def manual_unlock(self, operator: str, reason: str) -> bool:
        """
        手动解锁（需要人工审批）
        
        Args:
            operator: 操作人
            reason: 解锁原因
        
        Returns:
            是否解锁成功
        """
        if not self.engine.is_locked:
            return True
        
        logger.warning(
            f"手动解锁: operator={operator}, reason={reason}",
            extra={"operator": operator, "reason": reason},
        )
        
        self.engine.reset_to_normal()
        self._degraded_mode = True
        self._recovery_start = utc_now()
        
        return True
    
    async def check_exit_degraded(self, context: RiskContext) -> bool:
        """
        检查是否可以退出降级模式
        
        Args:
            context: 当前风控上下文
        
        Returns:
            是否可以退出降级模式
        """
        if not self._degraded_mode:
            return True
        
        if self._recovery_start is None:
            return False
        
        # 降级模式至少持续 24 小时
        elapsed = utc_now() - self._recovery_start
        if elapsed < timedelta(hours=24):
            return False
        
        # 检查风险指标是否恢复正常
        if context.drawdown >= RiskThresholds.account.max_drawdown * 0.5:
            return False
        
        if context.consecutive_losses >= 2:
            return False
        
        # 退出降级模式
        self._degraded_mode = False
        self._recovery_start = None
        logger.info("退出降级运行模式，恢复正常运行")
        
        return True
    
    def get_adjusted_position(self, requested_position: float) -> float:
        """
        获取调整后的仓位
        
        Args:
            requested_position: 请求的仓位
        
        Returns:
            调整后的仓位
        """
        return requested_position * self.position_limit_ratio
