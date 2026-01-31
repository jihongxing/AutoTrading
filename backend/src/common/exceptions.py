"""
BTC 自动交易系统 — 自定义异常

异常层级：
- TradingSystemError: 基础异常
  - ArchitectureViolationError: 架构违规（宪法级）
  - StrategyError: 策略层异常
  - RiskControlError: 风控层异常
  - ExecutionError: 执行层异常
  - StateMachineError: 状态机异常
  - DataError: 数据层异常
"""

from typing import Any


class TradingSystemError(Exception):
    """交易系统基础异常"""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ============================================================
# 宪法级异常（架构违规）
# ============================================================

class ArchitectureViolationError(TradingSystemError):
    """
    架构违规异常（宪法级）
    
    触发场景：
    - 策略直接下单
    - 绕过风控
    - 绕过状态机
    - 违反三权分立
    """
    pass


# ============================================================
# 策略层异常
# ============================================================

class StrategyError(TradingSystemError):
    """策略层异常"""
    pass


class InvalidClaimError(StrategyError):
    """无效的 Claim"""
    pass


class WitnessError(StrategyError):
    """证人异常"""
    pass


class WitnessMutedError(WitnessError):
    """证人已被静默"""
    pass


# ============================================================
# 风控层异常
# ============================================================

class RiskControlError(TradingSystemError):
    """风控层异常"""
    pass


class RiskVetoError(RiskControlError):
    """风控否决"""
    pass


class RiskLockedException(RiskControlError):
    """系统已被风控锁定"""
    pass


class DrawdownExceededError(RiskControlError):
    """回撤超限"""
    pass


# ============================================================
# 执行层异常
# ============================================================

class ExecutionError(TradingSystemError):
    """执行层异常"""
    pass


class OrderRejectedError(ExecutionError):
    """订单被拒绝"""
    pass


class OrderTimeoutError(ExecutionError):
    """订单超时"""
    pass


class SlippageExceededError(ExecutionError):
    """滑点超限"""
    pass


# ============================================================
# 状态机异常
# ============================================================

class StateMachineError(TradingSystemError):
    """状态机异常"""
    pass


class InvalidStateTransitionError(StateMachineError):
    """非法状态转换"""
    pass


class StateNotEligibleError(StateMachineError):
    """状态不允许交易"""
    pass


# ============================================================
# 数据层异常
# ============================================================

class DataError(TradingSystemError):
    """数据层异常"""
    pass


class DataNotFoundError(DataError):
    """数据未找到"""
    pass


class DataValidationError(DataError):
    """数据验证失败"""
    pass
