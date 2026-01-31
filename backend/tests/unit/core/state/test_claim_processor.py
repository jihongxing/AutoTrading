"""Claim 处理器测试"""

import pytest
from datetime import timedelta

from src.common.enums import ClaimType, RiskLevel, SystemState
from src.common.models import Claim
from src.common.utils import utc_now
from src.core.risk.base import RiskContext
from src.core.risk.engine import RiskControlEngine
from src.core.state.claim_processor import ClaimProcessor
from src.core.state.machine import StateMachine
from src.core.state.regime import RegimeManager, TradeRegime


@pytest.fixture
def state_machine():
    machine = StateMachine(initial_state=SystemState.OBSERVING)
    return machine


@pytest.fixture
def risk_engine():
    return RiskControlEngine()


@pytest.fixture
def regime_manager():
    return RegimeManager()


@pytest.fixture
def processor(state_machine, risk_engine, regime_manager):
    return ClaimProcessor(state_machine, risk_engine, regime_manager)


@pytest.fixture
def valid_claim():
    return Claim(
        strategy_id="test_strategy",
        claim_type=ClaimType.MARKET_ELIGIBLE,
        confidence=0.75,
        validity_window=300,
        direction="long",
    )


@pytest.fixture
def normal_risk_context():
    return RiskContext(
        equity=100000,
        initial_equity=100000,
        drawdown=0.05,
        daily_pnl=500,
        requested_position=0.02,
    )


class TestClaimProcessor:
    """Claim 处理器测试"""
    
    @pytest.mark.asyncio
    async def test_process_valid_claim(self, processor, valid_claim, normal_risk_context):
        """处理有效 Claim"""
        result = await processor.process_claim(valid_claim, normal_risk_context)
        
        assert result.success
        assert result.state_changed
        assert result.new_state == SystemState.ELIGIBLE
    
    @pytest.mark.asyncio
    async def test_expired_claim_rejected(self, processor, normal_risk_context):
        """过期 Claim 被拒绝"""
        expired_claim = Claim(
            strategy_id="test",
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=0.75,
            validity_window=60,
            timestamp=utc_now() - timedelta(seconds=120),
        )
        
        result = await processor.process_claim(expired_claim, normal_risk_context)
        
        assert not result.success
        assert "过期" in result.reason
    
    @pytest.mark.asyncio
    async def test_low_confidence_rejected(self, processor, normal_risk_context):
        """低置信度 Claim 被拒绝"""
        low_conf_claim = Claim(
            strategy_id="test",
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=0.3,
            validity_window=300,
        )
        
        result = await processor.process_claim(low_conf_claim, normal_risk_context)
        
        assert not result.success
        assert "置信度" in result.reason
    
    @pytest.mark.asyncio
    async def test_not_eligible_claim(self, processor, normal_risk_context):
        """市场不适合交易"""
        claim = Claim(
            strategy_id="test",
            claim_type=ClaimType.MARKET_NOT_ELIGIBLE,
            confidence=0.8,
            validity_window=300,
        )
        
        result = await processor.process_claim(claim, normal_risk_context)
        
        assert result.success
        assert not result.state_changed
        assert "不适合" in result.reason
    
    @pytest.mark.asyncio
    async def test_risk_rejected(self, processor, valid_claim):
        """风控拒绝"""
        high_risk_context = RiskContext(
            equity=75000,
            initial_equity=100000,
            drawdown=0.25,  # 超过阈值
            daily_pnl=-5000,
        )
        
        result = await processor.process_claim(valid_claim, high_risk_context)
        
        assert not result.success
        assert result.risk_result is not None
        assert not result.risk_result.approved
    
    @pytest.mark.asyncio
    async def test_wrong_state_rejected(self, processor, valid_claim, normal_risk_context):
        """非 OBSERVING 状态拒绝"""
        processor.state_machine._state = SystemState.COOLDOWN
        
        result = await processor.process_claim(valid_claim, normal_risk_context)
        
        assert not result.success
        assert "不接受" in result.reason
