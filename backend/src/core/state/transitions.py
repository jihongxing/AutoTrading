"""
BTC 自动交易系统 — 状态转换器

管理状态转换的条件检查和动作执行。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from src.common.enums import SystemState
from src.common.logging import get_logger
from src.common.utils import utc_now

from .states import is_valid_transition

logger = get_logger(__name__)


@dataclass
class TransitionRecord:
    """状态转换记录"""
    from_state: SystemState
    to_state: SystemState
    reason: str
    timestamp: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransitionResult:
    """状态转换结果"""
    success: bool
    from_state: SystemState
    to_state: SystemState
    reason: str
    error: str | None = None


class StateTransition:
    """
    状态转换器
    
    负责验证和执行状态转换。
    """
    
    def __init__(self):
        self._history: list[TransitionRecord] = []
        self._callbacks: dict[SystemState, list[Callable[[SystemState, SystemState], Any]]] = {}
    
    def can_transition(
        self,
        from_state: SystemState,
        to_state: SystemState,
    ) -> tuple[bool, str]:
        """
        检查是否可以转换
        
        Args:
            from_state: 当前状态
            to_state: 目标状态
        
        Returns:
            (是否可以转换, 原因)
        """
        if from_state == to_state:
            return False, "目标状态与当前状态相同"
        
        if not is_valid_transition(from_state, to_state):
            return False, f"不允许从 {from_state.value} 转换到 {to_state.value}"
        
        return True, "允许转换"
    
    async def execute(
        self,
        from_state: SystemState,
        to_state: SystemState,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> TransitionResult:
        """
        执行状态转换
        
        Args:
            from_state: 当前状态
            to_state: 目标状态
            reason: 转换原因
            metadata: 附加元数据
        
        Returns:
            转换结果
        """
        can_do, check_reason = self.can_transition(from_state, to_state)
        
        if not can_do:
            logger.warning(
                f"状态转换被拒绝: {from_state.value} -> {to_state.value}, 原因: {check_reason}"
            )
            return TransitionResult(
                success=False,
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                error=check_reason,
            )
        
        # 记录转换
        record = TransitionRecord(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            metadata=metadata or {},
        )
        self._history.append(record)
        
        logger.info(
            f"状态转换: {from_state.value} -> {to_state.value}, 原因: {reason}",
            extra={"from": from_state.value, "to": to_state.value},
        )
        
        # 执行回调
        await self._execute_callbacks(from_state, to_state)
        
        return TransitionResult(
            success=True,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
        )
    
    def register_callback(
        self,
        target_state: SystemState,
        callback: Callable[[SystemState, SystemState], Any],
    ) -> None:
        """注册状态转换回调"""
        if target_state not in self._callbacks:
            self._callbacks[target_state] = []
        self._callbacks[target_state].append(callback)
    
    async def _execute_callbacks(
        self,
        from_state: SystemState,
        to_state: SystemState,
    ) -> None:
        """执行状态转换回调"""
        callbacks = self._callbacks.get(to_state, [])
        for callback in callbacks:
            try:
                result = callback(from_state, to_state)
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.error(f"状态转换回调异常: {e}")
    
    def get_history(
        self,
        limit: int = 100,
    ) -> list[TransitionRecord]:
        """获取转换历史"""
        return self._history[-limit:]
    
    def get_last_transition(self) -> TransitionRecord | None:
        """获取最后一次转换"""
        return self._history[-1] if self._history else None
