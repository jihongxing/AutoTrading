"""
BTC 自动交易系统 — 状态持久化

状态存储和恢复。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.common.enums import SystemState
from src.common.logging import get_logger
from src.common.utils import utc_now

logger = get_logger(__name__)


@dataclass
class StateSnapshot:
    """状态快照"""
    state: SystemState
    entered_at: datetime
    metadata: dict[str, Any]
    snapshot_at: datetime


class StateStorage:
    """
    状态存储
    
    负责状态的持久化和恢复。
    """
    
    def __init__(self):
        self._snapshots: list[StateSnapshot] = []
        self._current_snapshot: StateSnapshot | None = None
    
    async def save_state(
        self,
        state: SystemState,
        entered_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        保存状态
        
        Args:
            state: 当前状态
            entered_at: 进入时间
            metadata: 附加元数据
        """
        snapshot = StateSnapshot(
            state=state,
            entered_at=entered_at,
            metadata=metadata or {},
            snapshot_at=utc_now(),
        )
        
        self._snapshots.append(snapshot)
        self._current_snapshot = snapshot
        
        logger.info(f"状态已保存: {state.value}")
    
    async def load_state(self) -> StateSnapshot | None:
        """
        加载最新状态
        
        Returns:
            状态快照，如果没有则返回 None
        """
        return self._current_snapshot
    
    async def get_history(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[StateSnapshot]:
        """
        获取状态历史
        
        Args:
            start: 开始时间
            end: 结束时间
            limit: 最大数量
        
        Returns:
            状态快照列表
        """
        result = self._snapshots
        
        if start:
            result = [s for s in result if s.snapshot_at >= start]
        if end:
            result = [s for s in result if s.snapshot_at <= end]
        
        return result[-limit:]
    
    async def get_state_duration(
        self,
        state: SystemState,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> float:
        """
        获取状态累计持续时间（秒）
        
        Args:
            state: 目标状态
            start: 开始时间
            end: 结束时间
        
        Returns:
            累计持续时间（秒）
        """
        history = await self.get_history(start, end, limit=10000)
        
        total_seconds = 0.0
        prev_snapshot: StateSnapshot | None = None
        
        for snapshot in history:
            if prev_snapshot and prev_snapshot.state == state:
                duration = (snapshot.snapshot_at - prev_snapshot.snapshot_at).total_seconds()
                total_seconds += duration
            prev_snapshot = snapshot
        
        # 如果当前状态是目标状态，加上到现在的时间
        if prev_snapshot and prev_snapshot.state == state:
            duration = (utc_now() - prev_snapshot.snapshot_at).total_seconds()
            total_seconds += duration
        
        return total_seconds
    
    async def clear_history(self) -> None:
        """清除历史"""
        self._snapshots = []
        if self._current_snapshot:
            self._snapshots.append(self._current_snapshot)
        logger.info("状态历史已清除")
