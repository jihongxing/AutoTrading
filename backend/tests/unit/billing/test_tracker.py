"""
收益跟踪器单元测试
"""

import pytest

from src.billing import FeeCalculator, ProfitTracker
from src.user.models import SubscriptionPlan


class TestFeeCalculator:
    """费用计算器测试"""
    
    def test_get_fee_rate(self):
        calc = FeeCalculator()
        
        assert calc.get_fee_rate(SubscriptionPlan.FREE) == 0.30
        assert calc.get_fee_rate(SubscriptionPlan.BASIC) == 0.20
        assert calc.get_fee_rate(SubscriptionPlan.PRO) == 0.10
    
    def test_calculate_platform_fee(self):
        calc = FeeCalculator()
        
        # 盈利收费
        fee = calc.calculate_platform_fee(100.0, 0.20)
        assert fee == 20.0
        
        # 亏损不收费
        fee = calc.calculate_platform_fee(-50.0, 0.20)
        assert fee == 0.0
    
    def test_calculate_user_net(self):
        calc = FeeCalculator()
        
        # 盈利
        net = calc.calculate_user_net(100.0, 0.20)
        assert net == 80.0
        
        # 亏损
        net = calc.calculate_user_net(-50.0, 0.20)
        assert net == -50.0
    
    def test_estimate_fees(self):
        calc = FeeCalculator()
        
        result = calc.estimate_fees(1000.0, SubscriptionPlan.BASIC)
        
        assert result["expected_profit"] == 1000.0
        assert result["fee_rate"] == 0.20
        assert result["platform_fee"] == 200.0
        assert result["monthly_subscription"] == 29.0


class TestProfitTracker:
    """收益跟踪器测试"""
    
    @pytest.fixture
    def tracker(self):
        return ProfitTracker()
    
    def test_record_trade_profit(self, tracker):
        profit = tracker.record_trade(
            user_id="user-001",
            trade_id="trade-001",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=100.0,
            fee_rate=0.20,
        )
        
        assert profit.realized_pnl == 100.0
        assert profit.platform_fee == 20.0
        assert profit.net_profit == 80.0
    
    def test_record_trade_loss(self, tracker):
        profit = tracker.record_trade(
            user_id="user-001",
            trade_id="trade-001",
            symbol="BTCUSDT",
            side="SELL",
            realized_pnl=-50.0,
            fee_rate=0.20,
        )
        
        assert profit.realized_pnl == -50.0
        assert profit.platform_fee == 0.0  # 亏损不收费
        assert profit.net_profit == -50.0
    
    def test_get_user_profits(self, tracker):
        tracker.record_trade(
            user_id="user-001",
            trade_id="trade-001",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=100.0,
            fee_rate=0.20,
        )
        tracker.record_trade(
            user_id="user-001",
            trade_id="trade-002",
            symbol="BTCUSDT",
            side="SELL",
            realized_pnl=-30.0,
            fee_rate=0.20,
        )
        
        profits = tracker.get_user_profits("user-001")
        assert len(profits) == 2
    
    def test_calculate_daily_profit(self, tracker):
        tracker.record_trade(
            user_id="user-001",
            trade_id="trade-001",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=100.0,
            fee_rate=0.20,
        )
        tracker.record_trade(
            user_id="user-001",
            trade_id="trade-002",
            symbol="BTCUSDT",
            side="SELL",
            realized_pnl=-30.0,
            fee_rate=0.20,
        )
        
        summary = tracker.calculate_daily_profit("user-001")
        
        assert summary.total_trades == 2
        assert summary.winning_trades == 1
        assert summary.losing_trades == 1
        assert summary.gross_profit == 100.0
        assert summary.gross_loss == 30.0
        assert summary.net_pnl == 70.0
        assert summary.platform_fees == 20.0
    
    def test_get_platform_total_fees(self, tracker):
        tracker.record_trade(
            user_id="user-001",
            trade_id="trade-001",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=100.0,
            fee_rate=0.20,
        )
        tracker.record_trade(
            user_id="user-002",
            trade_id="trade-002",
            symbol="BTCUSDT",
            side="BUY",
            realized_pnl=200.0,
            fee_rate=0.10,
        )
        
        total = tracker.get_platform_total_fees()
        assert total == 40.0  # 20 + 20
