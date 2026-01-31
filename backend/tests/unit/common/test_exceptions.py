"""异常测试"""

import pytest

from src.common.exceptions import (
    ArchitectureViolationError,
    DataError,
    DataNotFoundError,
    DataValidationError,
    DrawdownExceededError,
    ExecutionError,
    InvalidClaimError,
    InvalidStateTransitionError,
    OrderRejectedError,
    OrderTimeoutError,
    RiskControlError,
    RiskLockedException,
    RiskVetoError,
    SlippageExceededError,
    StateMachineError,
    StateNotEligibleError,
    StrategyError,
    TradingSystemError,
    WitnessError,
    WitnessMutedError,
)


class TestExceptionHierarchy:
    """异常层级测试"""
    
    def test_base_exception(self):
        """验证基础异常"""
        err = TradingSystemError("测试错误", {"key": "value"})
        assert err.message == "测试错误"
        assert err.details == {"key": "value"}
        assert str(err) == "测试错误"
    
    def test_architecture_violation(self):
        """验证架构违规异常"""
        err = ArchitectureViolationError("策略直接下单")
        assert isinstance(err, TradingSystemError)
    
    def test_strategy_exceptions(self):
        """验证策略层异常继承"""
        assert issubclass(InvalidClaimError, StrategyError)
        assert issubclass(WitnessMutedError, WitnessError)
        assert issubclass(WitnessError, StrategyError)
        assert issubclass(StrategyError, TradingSystemError)
    
    def test_risk_exceptions(self):
        """验证风控层异常继承"""
        assert issubclass(RiskVetoError, RiskControlError)
        assert issubclass(RiskLockedException, RiskControlError)
        assert issubclass(DrawdownExceededError, RiskControlError)
        assert issubclass(RiskControlError, TradingSystemError)
    
    def test_execution_exceptions(self):
        """验证执行层异常继承"""
        assert issubclass(OrderRejectedError, ExecutionError)
        assert issubclass(OrderTimeoutError, ExecutionError)
        assert issubclass(SlippageExceededError, ExecutionError)
        assert issubclass(ExecutionError, TradingSystemError)
    
    def test_state_machine_exceptions(self):
        """验证状态机异常继承"""
        assert issubclass(InvalidStateTransitionError, StateMachineError)
        assert issubclass(StateNotEligibleError, StateMachineError)
        assert issubclass(StateMachineError, TradingSystemError)
    
    def test_data_exceptions(self):
        """验证数据层异常继承"""
        assert issubclass(DataNotFoundError, DataError)
        assert issubclass(DataValidationError, DataError)
        assert issubclass(DataError, TradingSystemError)


class TestExceptionUsage:
    """异常使用测试"""
    
    def test_catch_specific(self):
        """验证可以捕获特定异常"""
        with pytest.raises(RiskVetoError):
            raise RiskVetoError("风控否决")
    
    def test_catch_parent(self):
        """验证可以通过父类捕获"""
        with pytest.raises(RiskControlError):
            raise RiskVetoError("风控否决")
    
    def test_catch_base(self):
        """验证可以通过基类捕获"""
        with pytest.raises(TradingSystemError):
            raise DataNotFoundError("数据未找到")
    
    def test_exception_details(self):
        """验证异常详情"""
        err = OrderRejectedError(
            "订单被拒绝",
            {"order_id": "o1", "reason": "余额不足"}
        )
        assert err.details["order_id"] == "o1"
        assert err.details["reason"] == "余额不足"
