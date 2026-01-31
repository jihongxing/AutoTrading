"""枚举测试"""

import pytest

from src.common.enums import (
    ClaimType,
    HealthGrade,
    OrderSide,
    OrderStatus,
    OrderType,
    RiskEventType,
    RiskLevel,
    SystemState,
    WitnessStatus,
    WitnessTier,
)


class TestSystemState:
    """系统状态枚举测试"""
    
    def test_all_states_defined(self):
        """验证所有状态已定义"""
        expected = {
            "SYSTEM_INIT", "OBSERVING", "ELIGIBLE",
            "ACTIVE_TRADING", "COOLDOWN", "RISK_LOCKED", "RECOVERY"
        }
        actual = {s.name for s in SystemState}
        assert actual == expected
    
    def test_str_serialization(self):
        """验证字符串序列化"""
        assert SystemState.OBSERVING.value == "observing"


class TestClaimType:
    """声明类型枚举测试"""
    
    def test_whitelist_types(self):
        """验证白名单类型"""
        expected = {
            "MARKET_ELIGIBLE", "MARKET_NOT_ELIGIBLE",
            "REGIME_MATCHED", "REGIME_CONFLICT", "EXECUTION_VETO"
        }
        actual = {c.name for c in ClaimType}
        assert actual == expected


class TestWitnessTier:
    """证人等级枚举测试"""
    
    def test_three_tiers(self):
        """验证三个等级"""
        assert len(WitnessTier) == 3
        assert WitnessTier.TIER_1.value == "tier_1"
        assert WitnessTier.TIER_2.value == "tier_2"
        assert WitnessTier.TIER_3.value == "tier_3"


class TestOrderEnums:
    """订单相关枚举测试"""
    
    def test_order_side(self):
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"
    
    def test_order_type(self):
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
    
    def test_order_status(self):
        expected = {
            "PENDING", "SUBMITTED", "FILLED",
            "PARTIALLY_FILLED", "CANCELLED", "REJECTED"
        }
        actual = {s.name for s in OrderStatus}
        assert actual == expected


class TestRiskEnums:
    """风控相关枚举测试"""
    
    def test_risk_level(self):
        expected = {"NORMAL", "WARNING", "COOLDOWN", "RISK_LOCKED"}
        actual = {r.name for r in RiskLevel}
        assert actual == expected
    
    def test_risk_event_type(self):
        assert RiskEventType.DRAWDOWN_EXCEEDED.value == "drawdown_exceeded"
        assert RiskEventType.CONSECUTIVE_LOSS.value == "consecutive_loss"


class TestHealthGrade:
    """健康度等级测试"""
    
    def test_four_grades(self):
        assert len(HealthGrade) == 4
        grades = [g.value for g in HealthGrade]
        assert grades == ["A", "B", "C", "D"]
