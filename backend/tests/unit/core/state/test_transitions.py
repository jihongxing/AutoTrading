"""状态转换测试"""

import pytest

from src.common.enums import SystemState
from src.core.state.transitions import StateTransition, TransitionResult
from src.core.state.states import is_valid_transition, FORBIDDEN_TRANSITIONS


class TestValidTransitions:
    """合法转换测试"""
    
    def test_init_to_observing(self):
        assert is_valid_transition(SystemState.SYSTEM_INIT, SystemState.OBSERVING)
    
    def test_observing_to_eligible(self):
        assert is_valid_transition(SystemState.OBSERVING, SystemState.ELIGIBLE)
    
    def test_eligible_to_active(self):
        assert is_valid_transition(SystemState.ELIGIBLE, SystemState.ACTIVE_TRADING)
    
    def test_active_to_cooldown(self):
        assert is_valid_transition(SystemState.ACTIVE_TRADING, SystemState.COOLDOWN)
    
    def test_cooldown_to_observing(self):
        assert is_valid_transition(SystemState.COOLDOWN, SystemState.OBSERVING)
    
    def test_any_to_risk_locked(self):
        """任意状态可以转到 RISK_LOCKED"""
        for state in SystemState:
            if state != SystemState.RISK_LOCKED:
                assert is_valid_transition(state, SystemState.RISK_LOCKED)
    
    def test_risk_locked_to_recovery(self):
        assert is_valid_transition(SystemState.RISK_LOCKED, SystemState.RECOVERY)
    
    def test_recovery_to_observing(self):
        assert is_valid_transition(SystemState.RECOVERY, SystemState.OBSERVING)


class TestForbiddenTransitions:
    """禁止转换测试"""
    
    def test_observing_to_active_forbidden(self):
        """不能绕过 ELIGIBLE"""
        assert not is_valid_transition(SystemState.OBSERVING, SystemState.ACTIVE_TRADING)
    
    def test_risk_locked_to_eligible_forbidden(self):
        """不能绕过 RECOVERY"""
        assert not is_valid_transition(SystemState.RISK_LOCKED, SystemState.ELIGIBLE)
    
    def test_cooldown_to_active_forbidden(self):
        """不能绕过 OBSERVING"""
        assert not is_valid_transition(SystemState.COOLDOWN, SystemState.ACTIVE_TRADING)


class TestStateTransition:
    """StateTransition 类测试"""
    
    @pytest.fixture
    def transition(self):
        return StateTransition()
    
    def test_can_transition_valid(self, transition):
        can, reason = transition.can_transition(
            SystemState.OBSERVING, SystemState.ELIGIBLE
        )
        assert can is True
    
    def test_can_transition_invalid(self, transition):
        can, reason = transition.can_transition(
            SystemState.OBSERVING, SystemState.ACTIVE_TRADING
        )
        assert can is False
    
    def test_can_transition_same_state(self, transition):
        can, reason = transition.can_transition(
            SystemState.OBSERVING, SystemState.OBSERVING
        )
        assert can is False
        assert "相同" in reason
    
    @pytest.mark.asyncio
    async def test_execute_success(self, transition):
        result = await transition.execute(
            SystemState.OBSERVING,
            SystemState.ELIGIBLE,
            "测试转换",
        )
        assert result.success is True
        assert result.from_state == SystemState.OBSERVING
        assert result.to_state == SystemState.ELIGIBLE
    
    @pytest.mark.asyncio
    async def test_execute_failure(self, transition):
        result = await transition.execute(
            SystemState.OBSERVING,
            SystemState.ACTIVE_TRADING,
            "非法转换",
        )
        assert result.success is False
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_history(self, transition):
        await transition.execute(SystemState.SYSTEM_INIT, SystemState.OBSERVING, "初始化")
        await transition.execute(SystemState.OBSERVING, SystemState.ELIGIBLE, "Claim")
        
        history = transition.get_history()
        assert len(history) == 2
        assert history[0].to_state == SystemState.OBSERVING
        assert history[1].to_state == SystemState.ELIGIBLE
