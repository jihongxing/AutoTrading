"""
BTC 自动交易系统 — 状态机核心

状态机是系统唯一交易入口，管理系统状态转换。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from src.common.enums import SystemState
from src.common.exceptions import InvalidStateTransitionError, StateNotEligibleError
from src.common.logging import get_logger
from src.common.utils import utc_now

from .states import get_state_metadata, is_valid_transition
from .transitions import StateTransition, TransitionResult

logger = get_logger(__name__)


class StateMachine:
    """
    全局状态机
    
    系统唯一交易入口，管理系统状态转换。
    """
    
    def __init__(self, initial_state: SystemState = SystemState.SYSTEM_INIT):
        self._state = initial_state
        self._state_entered_at = utc_now()
        self._transition = StateTransition()
        self._lock = asyncio.Lock()
    
    @property
    def current_state(self) -> SystemState:
        """当前状态"""
        return self._state
    
    @property
    def state_duration(self) -> timedelta:
        """当前状态持续时间"""
        return utc_now() - self._state_entered_at
    
    @property
    def is_trading_allowed(self) -> bool:
        """是否允许交易"""
        metadata = get_state_metadata(self._state)
        return metadata.allows_trading
    
    @property
    def is_locked(self) -> bool:
        """是否被锁定"""
        return self._state == SystemState.RISK_LOCKED
    
    def can_transition(self, target: SystemState) -> bool:
        """检查是否可以转换到目标状态"""
        return is_valid_transition(self._state, target)
    
    async def transition(
        self,
        target: SystemState,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> TransitionResult:
        """
        执行状态转换
        
        Args:
            target: 目标状态
            reason: 转换原因
            metadata: 附加元数据
        
        Returns:
            转换结果
        """
        async with self._lock:
            result = await self._transition.execute(
                from_state=self._state,
                to_state=target,
                reason=reason,
                metadata=metadata,
            )
            
            if result.success:
                self._state = target
                self._state_entered_at = utc_now()
            
            return result
    
    async def force_lock(self, reason: str) -> TransitionResult:
        """
        强制锁定（风控触发）
        
        Args:
            reason: 锁定原因
        
        Returns:
            转换结果
        """
        logger.warning(f"强制锁定: {reason}")
        return await self.transition(
            target=SystemState.RISK_LOCKED,
            reason=f"风控强制锁定: {reason}",
        )
    
    async def start_recovery(self, reason: str) -> TransitionResult:
        """
        开始恢复
        
        Args:
            reason: 恢复原因
        
        Returns:
            转换结果
        """
        if self._state != SystemState.RISK_LOCKED:
            raise InvalidStateTransitionError(
                f"只能从 RISK_LOCKED 状态开始恢复，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.RECOVERY,
            reason=reason,
        )
    
    async def complete_recovery(self) -> TransitionResult:
        """完成恢复，返回观察状态"""
        if self._state != SystemState.RECOVERY:
            raise InvalidStateTransitionError(
                f"只能从 RECOVERY 状态完成恢复，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.OBSERVING,
            reason="恢复完成",
        )
    
    async def initialize_complete(self) -> TransitionResult:
        """初始化完成"""
        if self._state != SystemState.SYSTEM_INIT:
            raise InvalidStateTransitionError(
                f"只能从 SYSTEM_INIT 状态完成初始化，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.OBSERVING,
            reason="系统初始化完成",
        )
    
    async def become_eligible(self, reason: str) -> TransitionResult:
        """进入允许交易状态"""
        if self._state != SystemState.OBSERVING:
            raise StateNotEligibleError(
                f"只能从 OBSERVING 状态进入 ELIGIBLE，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.ELIGIBLE,
            reason=reason,
        )
    
    async def start_trading(self, reason: str) -> TransitionResult:
        """开始交易"""
        if self._state != SystemState.ELIGIBLE:
            raise StateNotEligibleError(
                f"只能从 ELIGIBLE 状态开始交易，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.ACTIVE_TRADING,
            reason=reason,
        )
    
    async def complete_trading(self, reason: str) -> TransitionResult:
        """完成交易，进入冷却"""
        if self._state != SystemState.ACTIVE_TRADING:
            raise InvalidStateTransitionError(
                f"只能从 ACTIVE_TRADING 状态完成交易，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.COOLDOWN,
            reason=reason,
        )
    
    async def complete_cooldown(self) -> TransitionResult:
        """完成冷却，返回观察"""
        if self._state != SystemState.COOLDOWN:
            raise InvalidStateTransitionError(
                f"只能从 COOLDOWN 状态完成冷却，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.OBSERVING,
            reason="冷却完成",
        )
    
    async def cancel_eligible(self, reason: str) -> TransitionResult:
        """取消允许交易状态"""
        if self._state != SystemState.ELIGIBLE:
            raise InvalidStateTransitionError(
                f"只能从 ELIGIBLE 状态取消，当前状态: {self._state.value}"
            )
        return await self.transition(
            target=SystemState.OBSERVING,
            reason=reason,
        )
    
    def get_transition_history(self, limit: int = 100) -> list[Any]:
        """获取状态转换历史"""
        return self._transition.get_history(limit)
    
    def check_timeout(self) -> bool:
        """检查当前状态是否超时"""
        metadata = get_state_metadata(self._state)
        if metadata.timeout_seconds is None:
            return False
        return self.state_duration > timedelta(seconds=metadata.timeout_seconds)
