"""
BTC 自动交易系统 — 统计分析器

计算成功率、盈亏统计和回撤统计。
"""

import statistics
from dataclasses import dataclass
from datetime import datetime

from src.common.logging import get_logger

from .collector import TradeData

logger = get_logger(__name__)


@dataclass
class PnLStatistics:
    """盈亏统计"""
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float  # 总盈利 / 总亏损
    expectancy: float  # 期望值


@dataclass
class DrawdownStatistics:
    """回撤统计"""
    max_drawdown: float
    max_drawdown_pct: float
    avg_drawdown: float
    drawdown_duration_avg: int  # 秒
    current_drawdown: float
    recovery_rate: float


@dataclass
class PeriodStatistics:
    """周期统计"""
    period: str  # daily/weekly/monthly
    start_time: datetime
    end_time: datetime
    pnl_stats: PnLStatistics
    drawdown_stats: DrawdownStatistics


class StatisticsAnalyzer:
    """
    统计分析器
    
    计算各类统计指标：
    - 成功率
    - 盈亏统计
    - 回撤统计
    """
    
    def calculate_pnl_statistics(self, trades: list[TradeData]) -> PnLStatistics:
        """
        计算盈亏统计
        
        Args:
            trades: 交易数据列表
        
        Returns:
            盈亏统计
        """
        if not trades:
            return PnLStatistics(
                total_trades=0,
                win_count=0,
                loss_count=0,
                win_rate=0.0,
                total_pnl=0.0,
                avg_pnl=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                expectancy=0.0,
            )
        
        wins = [t for t in trades if t.is_win]
        losses = [t for t in trades if not t.is_win]
        
        win_count = len(wins)
        loss_count = len(losses)
        total_trades = len(trades)
        
        win_rate = win_count / total_trades
        
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / total_trades
        
        total_wins = sum(t.pnl for t in wins)
        total_losses = abs(sum(t.pnl for t in losses))
        
        avg_win = total_wins / win_count if win_count > 0 else 0.0
        avg_loss = total_losses / loss_count if loss_count > 0 else 0.0
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # 期望值 = 胜率 * 平均盈利 - 败率 * 平均亏损
        expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
        
        return PnLStatistics(
            total_trades=total_trades,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
        )
    
    def calculate_drawdown_statistics(
        self,
        trades: list[TradeData],
        initial_capital: float = 100000.0,
    ) -> DrawdownStatistics:
        """
        计算回撤统计
        
        Args:
            trades: 交易数据列表（按时间排序）
            initial_capital: 初始资金
        
        Returns:
            回撤统计
        """
        if not trades:
            return DrawdownStatistics(
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                avg_drawdown=0.0,
                drawdown_duration_avg=0,
                current_drawdown=0.0,
                recovery_rate=0.0,
            )
        
        # 按时间排序
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        
        # 计算权益曲线
        equity = initial_capital
        peak = equity
        drawdowns = []
        drawdown_durations = []
        current_dd_start = None
        
        for trade in sorted_trades:
            equity += trade.pnl
            
            if equity > peak:
                peak = equity
                if current_dd_start is not None:
                    # 回撤结束
                    duration = (trade.timestamp - current_dd_start).total_seconds()
                    drawdown_durations.append(int(duration))
                    current_dd_start = None
            else:
                dd = (peak - equity) / peak
                drawdowns.append(dd)
                if current_dd_start is None:
                    current_dd_start = trade.timestamp
        
        max_dd = max(drawdowns) if drawdowns else 0.0
        avg_dd = statistics.mean(drawdowns) if drawdowns else 0.0
        avg_duration = int(statistics.mean(drawdown_durations)) if drawdown_durations else 0
        
        current_dd = (peak - equity) / peak if peak > 0 else 0.0
        
        # 恢复率：从回撤中恢复的次数 / 总回撤次数
        recovery_count = len(drawdown_durations)
        total_dd_count = len([d for d in drawdowns if d > 0.01])  # 忽略小于 1% 的回撤
        recovery_rate = recovery_count / total_dd_count if total_dd_count > 0 else 1.0
        
        return DrawdownStatistics(
            max_drawdown=max_dd * initial_capital,
            max_drawdown_pct=max_dd,
            avg_drawdown=avg_dd,
            drawdown_duration_avg=avg_duration,
            current_drawdown=current_dd,
            recovery_rate=recovery_rate,
        )
    
    def calculate_period_statistics(
        self,
        trades: list[TradeData],
        period: str,
        start_time: datetime,
        end_time: datetime,
        initial_capital: float = 100000.0,
    ) -> PeriodStatistics:
        """
        计算周期统计
        
        Args:
            trades: 交易数据列表
            period: 周期类型
            start_time: 开始时间
            end_time: 结束时间
            initial_capital: 初始资金
        
        Returns:
            周期统计
        """
        # 过滤时间范围内的交易
        period_trades = [
            t for t in trades
            if start_time <= t.timestamp <= end_time
        ]
        
        pnl_stats = self.calculate_pnl_statistics(period_trades)
        drawdown_stats = self.calculate_drawdown_statistics(period_trades, initial_capital)
        
        logger.info(
            f"周期统计: {period}, 交易数: {pnl_stats.total_trades}, 胜率: {pnl_stats.win_rate:.2%}",
            extra={"period": period, "trades": pnl_stats.total_trades, "win_rate": pnl_stats.win_rate},
        )
        
        return PeriodStatistics(
            period=period,
            start_time=start_time,
            end_time=end_time,
            pnl_stats=pnl_stats,
            drawdown_stats=drawdown_stats,
        )
    
    def calculate_sharpe_ratio(
        self,
        trades: list[TradeData],
        risk_free_rate: float = 0.02,
        periods_per_year: int = 365,
    ) -> float:
        """
        计算夏普比率
        
        Args:
            trades: 交易数据列表
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 每年周期数
        
        Returns:
            夏普比率
        """
        if len(trades) < 2:
            return 0.0
        
        returns = [t.pnl for t in trades]
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        # 年化
        annualized_return = avg_return * periods_per_year
        annualized_std = std_return * (periods_per_year ** 0.5)
        
        sharpe = (annualized_return - risk_free_rate) / annualized_std
        
        return sharpe
