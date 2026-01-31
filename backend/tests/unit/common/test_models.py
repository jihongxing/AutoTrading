"""数据模型测试"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.common.models import (
    Claim,
    ExecutionResult,
    FundingRate,
    Liquidation,
    MarketBar,
    Order,
    RiskCheckResult,
    RiskEvent,
    WitnessHealth,
)
from src.common.enums import (
    ClaimType,
    HealthGrade,
    OrderSide,
    OrderStatus,
    OrderType,
    RiskEventType,
    RiskLevel,
    WitnessStatus,
    WitnessTier,
)


class TestClaim:
    """Claim 模型测试"""
    
    def test_valid_claim(self):
        """验证有效 Claim"""
        claim = Claim(
            strategy_id="test_strategy",
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=0.75,
            validity_window=300,
            direction="long",
        )
        assert claim.strategy_id == "test_strategy"
        assert claim.confidence == 0.75
        assert claim.direction == "long"
    
    def test_frozen_model(self):
        """验证模型不可变"""
        claim = Claim(
            strategy_id="test",
            claim_type=ClaimType.MARKET_ELIGIBLE,
            confidence=0.5,
            validity_window=60,
        )
        with pytest.raises(ValidationError):
            claim.confidence = 0.8  # type: ignore
    
    def test_confidence_bounds(self):
        """验证置信度边界"""
        with pytest.raises(ValidationError):
            Claim(
                strategy_id="test",
                claim_type=ClaimType.MARKET_ELIGIBLE,
                confidence=1.5,  # 超出范围
                validity_window=60,
            )
    
    def test_invalid_direction(self):
        """验证方向校验"""
        with pytest.raises(ValidationError):
            Claim(
                strategy_id="test",
                claim_type=ClaimType.MARKET_ELIGIBLE,
                confidence=0.5,
                validity_window=60,
                direction="invalid",
            )
    
    def test_validity_window_positive(self):
        """验证有效窗口必须为正"""
        with pytest.raises(ValidationError):
            Claim(
                strategy_id="test",
                claim_type=ClaimType.MARKET_ELIGIBLE,
                confidence=0.5,
                validity_window=0,
            )


class TestWitnessHealth:
    """WitnessHealth 模型测试"""
    
    def test_valid_health(self):
        health = WitnessHealth(
            witness_id="w1",
            tier=WitnessTier.TIER_1,
            win_rate=0.55,
            sample_count=100,
        )
        assert health.status == WitnessStatus.ACTIVE
        assert health.grade == HealthGrade.B
        assert health.weight == 0.5
    
    def test_weight_bounds(self):
        """验证权重边界 [0.1, 0.9]"""
        with pytest.raises(ValidationError):
            WitnessHealth(
                witness_id="w1",
                tier=WitnessTier.TIER_1,
                win_rate=0.55,
                sample_count=100,
                weight=0.05,  # 低于下限
            )


class TestOrder:
    """Order 模型测试"""
    
    def test_market_order(self):
        order = Order(
            order_id="o1",
            side=OrderSide.BUY,
            quantity=0.1,
            strategy_id="s1",
        )
        assert order.order_type == OrderType.MARKET
        assert order.price is None
        assert order.status == OrderStatus.PENDING
    
    def test_limit_order(self):
        order = Order(
            order_id="o2",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000.0,
            strategy_id="s1",
        )
        assert order.price == 50000.0


class TestRiskModels:
    """风控模型测试"""
    
    def test_risk_event(self):
        event = RiskEvent(
            event_id="e1",
            event_type=RiskEventType.DRAWDOWN_EXCEEDED,
            level=RiskLevel.RISK_LOCKED,
            description="回撤超过 20%",
            value=0.22,
            threshold=0.20,
        )
        assert event.event_type == RiskEventType.DRAWDOWN_EXCEEDED
    
    def test_risk_check_result(self):
        result = RiskCheckResult(
            approved=False,
            level=RiskLevel.WARNING,
            reason="接近回撤阈值",
        )
        assert not result.approved
        assert result.events == []


class TestMarketData:
    """市场数据模型测试"""
    
    def test_market_bar(self):
        bar = MarketBar(
            ts=1704067200000,
            interval="1h",
            open=42000.0,
            high=42500.0,
            low=41800.0,
            close=42300.0,
            volume=1000.0,
        )
        assert bar.symbol == "BTCUSDT"
        assert bar.close == 42300.0
    
    def test_funding_rate(self):
        fr = FundingRate(
            ts=1704067200000,
            funding_rate=0.0001,
            mark_price=42000.0,
            index_price=41990.0,
        )
        assert fr.funding_rate == 0.0001
    
    def test_liquidation(self):
        liq = Liquidation(
            ts=1704067200000,
            side="LONG",
            quantity=1.5,
            price=41000.0,
            usd_value=61500.0,
        )
        assert liq.side == "LONG"
