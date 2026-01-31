"""
BTC 自动交易系统 — 全局状态机

状态机是系统唯一交易入口。
"""

from .claim_processor import ClaimProcessor, ProcessResult
from .machine import StateMachine
from .regime import RegimeConstraints, RegimeManager, RegimeOutput, TradeRegime
from .service import StateMachineService
from .service import StateMachineService as StateService  # 别名
from .states import (
    FORBIDDEN_TRANSITIONS,
    STATE_METADATA,
    VALID_TRANSITIONS,
    StateMetadata,
    get_state_metadata,
    is_valid_transition,
)
from .storage import StateSnapshot, StateStorage
from .transitions import StateTransition, TransitionRecord, TransitionResult

__all__ = [
    # States
    "StateMetadata",
    "STATE_METADATA",
    "VALID_TRANSITIONS",
    "FORBIDDEN_TRANSITIONS",
    "get_state_metadata",
    "is_valid_transition",
    # Transitions
    "StateTransition",
    "TransitionRecord",
    "TransitionResult",
    # Machine
    "StateMachine",
    # Claim Processor
    "ClaimProcessor",
    "ProcessResult",
    # Regime
    "TradeRegime",
    "RegimeConstraints",
    "RegimeManager",
    "RegimeOutput",
    # Storage
    "StateStorage",
    "StateSnapshot",
    # Service
    "StateMachineService",
    "StateService",  # 别名
]
