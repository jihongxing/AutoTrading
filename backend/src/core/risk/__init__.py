"""
BTC 自动交易系统 — 内核级风控

风控拥有硬否决权，保护系统长期生存。
"""

from .account_risk import AccountRiskChecker
from .base import RiskChecker, RiskContext
from .behavior_risk import BehaviorRiskChecker
from .constants import RiskThresholds
from .engine import RiskControlEngine
from .engine import RiskControlEngine as RiskEngine  # 别名
from .execution_risk import ExecutionRiskChecker
from .recovery import RecoveryManager
from .regime_risk import RegimeRiskChecker
from .system_risk import SystemRiskChecker

__all__ = [
    # Base
    "RiskChecker",
    "RiskContext",
    # Checkers
    "AccountRiskChecker",
    "BehaviorRiskChecker",
    "ExecutionRiskChecker",
    "RegimeRiskChecker",
    "SystemRiskChecker",
    # Engine
    "RiskControlEngine",
    "RiskEngine",  # 别名
    # Recovery
    "RecoveryManager",
    # Constants
    "RiskThresholds",
]
