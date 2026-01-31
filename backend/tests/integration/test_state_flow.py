"""状态机流程集成测试"""

import pytest

from src.common.enums import ClaimType, SystemState
from src.common.models import Claim
from src.core.risk.base import RiskContext
from src.core.state.service import StateMachineService
from src.core.state.regime import TradeRegime


@pytest.fixture
def service():
    return StateMachineService()


@pytest.fixture
def valid_claim():
    return Claim(
        strategy_id="test_strategy",
        claim_type=ClaimType.MARKET_ELIGIBLE,
        confidence=0.75,
        validity_window=300,
        direction="long",
        constraints={"regime": "volatility_expansion"},
    )


@pytest.fixture
def normal_context():
    return RiskContext(
        equity=100000,
        initial_equity=100000,
        drawdown=0.05,
        daily_pnl=500,
        requested_position=0.02,
    )


class TestStateMachineServiceIntegration:
    """状态机服务集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_trading_flow(self, service, valid_claim, normal_context):
        """完整交易流程"""
        # 初始化
        assert await service.initialize()
        assert service.get_current_state() == SystemState.OBSERVING
        
        # 提交 Claim
        result = await service.submit_claim(valid_claim, normal_context)
        assert result.success
        assert service.get_current_state() == SystemState.ELIGIBLE
        assert service.is_trading_allowed()
        
        # 检查范式
        regime = service.get_current_regime()
        assert regime == TradeRegime.VOLATILITY_EXPANSION
        
        # 开始交易
        assert await service.start_trading("执行交易")
        assert service.get_current_state() == SystemState.ACTIVE_TRADING
        
        # 完成交易
        assert await service.complete_trading("交易完成")
        assert service.get_current_state() == SystemState.COOLDOWN
        assert service.get_current_regime() is None  # 范式已清除
        
        # 完成冷却
        assert await service.complete_cooldown()
        assert service.get_current_state() == SystemState.OBSERVING
    
    @pytest.mark.asyncio
    async def test_risk_lock_flow(self, service, valid_claim):
        """风控锁定流程"""
        await service.initialize()
        
        # 高风险上下文
        high_risk_context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,
            daily_pnl=-5000,
        )
        
        # 提交 Claim 触发风控
        result = await service.submit_claim(valid_claim, high_risk_context)
        assert not result.success
        assert service.is_locked()
        
        # 开始恢复
        assert await service.start_recovery("解锁条件满足")
        assert service.get_current_state() == SystemState.RECOVERY
        
        # 完成恢复
        assert await service.complete_recovery()
        assert service.get_current_state() == SystemState.OBSERVING
    
    @pytest.mark.asyncio
    async def test_cancel_eligible(self, service, valid_claim, normal_context):
        """取消 ELIGIBLE 状态"""
        await service.initialize()
        await service.submit_claim(valid_claim, normal_context)
        
        assert service.get_current_state() == SystemState.ELIGIBLE
        
        # 取消
        assert await service.cancel_eligible("超时")
        assert service.get_current_state() == SystemState.OBSERVING
        assert service.get_current_regime() is None
    
    @pytest.mark.asyncio
    async def test_state_history(self, service, valid_claim, normal_context):
        """状态历史记录"""
        await service.initialize()
        await service.submit_claim(valid_claim, normal_context)
        await service.start_trading("交易")
        await service.complete_trading("完成")
        
        history = service.get_state_history()
        assert len(history) >= 4
