"""
BTC 自动交易系统 — 状态定义

状态机是系统唯一交易入口。
"""

from dataclasses import dataclass
from typing import Any

from src.common.enums import SystemState


@dataclass(frozen=True)
class StateMetadata:
    """状态元数据"""
    name: str
    description: str
    layer: int  # 1=系统存在态, 2=交易许可态
    allows_trading: bool
    timeout_seconds: int | None = None


# 状态元数据定义
STATE_METADATA: dict[SystemState, StateMetadata] = {
    SystemState.SYSTEM_INIT: StateMetadata(
        name="系统初始化",
        description="系统启动中，等待初始化完成",
        layer=1,
        allows_trading=False,
        timeout_seconds=60,
    ),
    SystemState.OBSERVING: StateMetadata(
        name="观察市场",
        description="观察市场状态，等待策略信号",
        layer=2,
        allows_trading=False,
    ),
    SystemState.ELIGIBLE: StateMetadata(
        name="允许交易",
        description="策略信号有效，风控批准，可以执行交易",
        layer=2,
        allows_trading=True,
        timeout_seconds=300,  # 5 分钟内必须执行
    ),
    SystemState.ACTIVE_TRADING: StateMetadata(
        name="交易中",
        description="正在执行交易",
        layer=2,
        allows_trading=True,
        timeout_seconds=60,
    ),
    SystemState.COOLDOWN: StateMetadata(
        name="冷却期",
        description="交易完成，等待冷却",
        layer=2,
        allows_trading=False,
        timeout_seconds=600,  # 默认 10 分钟
    ),
    SystemState.RISK_LOCKED: StateMetadata(
        name="风控锁定",
        description="风控触发，系统锁定",
        layer=1,
        allows_trading=False,
    ),
    SystemState.RECOVERY: StateMetadata(
        name="恢复期",
        description="从风控锁定恢复中",
        layer=1,
        allows_trading=False,
        timeout_seconds=3600,
    ),
}


# 合法状态转换规则
VALID_TRANSITIONS: dict[SystemState, set[SystemState]] = {
    SystemState.SYSTEM_INIT: {SystemState.OBSERVING, SystemState.RISK_LOCKED},
    SystemState.OBSERVING: {SystemState.ELIGIBLE, SystemState.RISK_LOCKED},
    SystemState.ELIGIBLE: {SystemState.ACTIVE_TRADING, SystemState.OBSERVING, SystemState.RISK_LOCKED},
    SystemState.ACTIVE_TRADING: {SystemState.COOLDOWN, SystemState.RISK_LOCKED},
    SystemState.COOLDOWN: {SystemState.OBSERVING, SystemState.RISK_LOCKED},
    SystemState.RISK_LOCKED: {SystemState.RECOVERY},
    SystemState.RECOVERY: {SystemState.OBSERVING, SystemState.RISK_LOCKED},
}


# 禁止的状态转换（显式定义）
FORBIDDEN_TRANSITIONS: set[tuple[SystemState, SystemState]] = {
    (SystemState.OBSERVING, SystemState.ACTIVE_TRADING),  # 绕过 ELIGIBLE
    (SystemState.RISK_LOCKED, SystemState.ELIGIBLE),      # 绕过 RECOVERY
    (SystemState.COOLDOWN, SystemState.ACTIVE_TRADING),   # 绕过 OBSERVING
    (SystemState.COOLDOWN, SystemState.ELIGIBLE),         # 绕过 OBSERVING
}


def is_valid_transition(from_state: SystemState, to_state: SystemState) -> bool:
    """检查状态转换是否合法"""
    if (from_state, to_state) in FORBIDDEN_TRANSITIONS:
        return False
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def get_state_metadata(state: SystemState) -> StateMetadata:
    """获取状态元数据"""
    return STATE_METADATA.get(state, StateMetadata(
        name=state.value,
        description="未知状态",
        layer=0,
        allows_trading=False,
    ))
