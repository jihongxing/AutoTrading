"""
BTC 自动交易系统 — 收益跟踪器
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

from .calculator import FeeCalculator
from .models import ProfitSummary, UserProfit

logger = get_logger(__name__)


class ProfitTracker:
    """
    收益跟踪器
    
    记录和统计用户交易收益。
    """
    
    def __init__(self, fee_calculator: FeeCalculator | None = None):
        self.fee_calculator = fee_calculator or FeeCalculator()
        # 内存存储（生产环境应使用数据库）
        self._profits: dict[str, list[UserProfit]] = defaultdict(list)
    
    def record_trade(
        self,
        user_id: str,
        trade_id: str,
        symbol: str,
        side: str,
        realized_pnl: float,
        fee_rate: float,
    ) -> UserProfit:
        """
        记录交易收益
        
        Args:
            user_id: 用户 ID
            trade_id: 交易 ID
            symbol: 交易对
            side: 方向
            realized_pnl: 已实现盈亏
            fee_rate: 费率
        
        Returns:
            收益记录
        """
        # 计算平台费用（仅对盈利收费）
        platform_fee = 0.0
        if realized_pnl > 0:
            platform_fee = self.fee_calculator.calculate_platform_fee(
                realized_pnl, fee_rate
            )
        
        net_profit = realized_pnl - platform_fee
        
        profit = UserProfit(
            user_id=user_id,
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            realized_pnl=realized_pnl,
            fee_rate=fee_rate,
            platform_fee=platform_fee,
            net_profit=net_profit,
        )
        
        self._profits[user_id].append(profit)
        
        logger.info(
            f"收益记录: user={user_id}, pnl={realized_pnl:.2f}, "
            f"fee={platform_fee:.2f}, net={net_profit:.2f}"
        )
        
        return profit
    
    def get_user_profits(
        self,
        user_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UserProfit]:
        """获取用户收益记录"""
        profits = self._profits.get(user_id, [])
        
        if start_time:
            profits = [p for p in profits if p.timestamp >= start_time]
        if end_time:
            profits = [p for p in profits if p.timestamp <= end_time]
        
        return profits
    
    def calculate_daily_profit(
        self,
        user_id: str,
        date: datetime | None = None,
    ) -> ProfitSummary:
        """计算日收益"""
        if date is None:
            date = utc_now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        return self._calculate_summary(user_id, "daily", start, end)
    
    def calculate_weekly_profit(
        self,
        user_id: str,
        date: datetime | None = None,
    ) -> ProfitSummary:
        """计算周收益"""
        if date is None:
            date = utc_now()
        
        # 找到本周一
        start = date - timedelta(days=date.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        
        return self._calculate_summary(user_id, "weekly", start, end)
    
    def calculate_monthly_profit(
        self,
        user_id: str,
        date: datetime | None = None,
    ) -> ProfitSummary:
        """计算月收益"""
        if date is None:
            date = utc_now()
        
        start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 下个月第一天
        if date.month == 12:
            end = start.replace(year=date.year + 1, month=1)
        else:
            end = start.replace(month=date.month + 1)
        
        return self._calculate_summary(user_id, "monthly", start, end)
    
    def calculate_period_profit(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> ProfitSummary:
        """计算指定时间段收益"""
        return self._calculate_summary(user_id, "custom", start_time, end_time)
    
    def _calculate_summary(
        self,
        user_id: str,
        period: str,
        start: datetime,
        end: datetime,
    ) -> ProfitSummary:
        """计算收益汇总"""
        profits = self.get_user_profits(user_id, start, end)
        
        summary = ProfitSummary(
            user_id=user_id,
            period=period,
            start_date=start,
            end_date=end,
        )
        
        for p in profits:
            summary.total_trades += 1
            summary.platform_fees += p.platform_fee
            
            if p.realized_pnl > 0:
                summary.winning_trades += 1
                summary.gross_profit += p.realized_pnl
            else:
                summary.losing_trades += 1
                summary.gross_loss += abs(p.realized_pnl)
            
            summary.net_pnl += p.realized_pnl
            summary.user_net_profit += p.net_profit
        
        return summary
    
    def get_all_profits(self) -> dict[str, list[UserProfit]]:
        """获取所有收益记录"""
        return dict(self._profits)
    
    def get_platform_total_fees(self) -> float:
        """获取平台总费用"""
        total = 0.0
        for profits in self._profits.values():
            total += sum(p.platform_fee for p in profits)
        return total
