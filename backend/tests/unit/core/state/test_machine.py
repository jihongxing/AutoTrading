"""状态机测试"""

import pytest

from src.common.enums import SystemState
from src.common.exceptions import InvalidStateTransitionError, StateNotEligibleError
from src.core.state.machine import StateMachine


@pytest.fixture
def machine():
    return StateMachine()


class TestStateMachine:
    """状态机测试"""
    
    def test_initial_state(self, machine):
        assert machine.current_state == SystemState.SYSTEM_INIT
        assert not machine.is_trading_allowed
        assert not machine.is_locked
    
    @pytest.mark.asyncio
    async def test_initialize_complete(self, machine):
        result = await machine.initialize_complete()
        assert result.success
        assert machine.current_state == SystemState.OBSERVING
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle(self, machine):
        """完整交易周期"""
        # 初始化
        await machine.initialize_complete()
        assert machine.current_state == SystemState.OBSERVING
        
        # 进入 ELIGIBLE
        await machine.become_eligible("Claim 批准")
        assert machine.current_state == SystemState.ELIGIBLE
        assert machine.is_trading_allowed
        
        # 开始交易
        await machine.start_trading("执行交易")
        assert machine.current_state == SystemState.ACTIVE_TRADING
        
        # 完成交易
        await machine.complete_trading("交易完成")
        assert machine.current_state == SystemState.COOLDOWN
        
        # 完成冷却
        await machine.complete_cooldown()
        assert machine.current_state == SystemState.OBSERVING
    
    @pytest.mark.asyncio
    async def test_force_lock(self, machine):
        """强制锁定"""
        await machine.initialize_complete()
        await machine.force_lock("风控触发")
        
        assert machine.current_state == SystemState.RISK_LOCKED
        assert machine.is_locked
    
    @pytest.mark.asyncio
    async def test_recovery_flow(self, machine):
        """恢复流程"""
        await machine.initialize_complete()
        await machine.force_lock("测试")
        
        await machine.start_recovery("解锁条件满足")
        assert machine.current_state == SystemState.RECOVERY
        
        await machine.complete_recovery()
        assert machine.current_state == SystemState.OBSERVING
    
    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self, machine):
        """非法转换抛出异常"""
        await machine.initialize_complete()
        
        with pytest.raises(StateNotEligibleError):
            await machine.start_trading("非法")
    
    @pytest.mark.asyncio
    async def test_cancel_eligible(self, machine):
        """取消 ELIGIBLE"""
        await machine.initialize_complete()
        await machine.become_eligible("测试")
        
        await machine.cancel_eligible("超时")
        assert machine.current_state == SystemState.OBSERVING
    
    def test_can_transition(self, machine):
        assert machine.can_transition(SystemState.OBSERVING)
        assert not machine.can_transition(SystemState.ACTIVE_TRADING)
