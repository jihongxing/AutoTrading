"""
BTC 自动交易系统 — 影子运行器

运行 SHADOW 状态的策略，记录模拟交易，评估绩效。
"""

from datetime import timedelta

from src.common.logging import get_logger
from src.common.models import Claim, MarketBar
from src.common.utils import utc_now

from ..base import BaseStrategy
from .models import ShadowPerformance, ShadowTradeRecord

logger = get_logger(__name__)


# 晋升条件
MIN_SHADOW_DAYS = 7
MIN_WIN_RATE = 0.51
MIN_TRADES = 10


class ShadowRunner:
    """
    影子运行器
    
    运行 SHADOW 策略，记录模拟交易，评估是否可晋升。
    """
    
    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}
        self._records: dict[str, list[ShadowTradeRecord]] = {}
        self._start_times: dict[str, float] = {}
    
    def register_strategy(self, strategy: BaseStrategy) -> None:
        """注册影子策略"""
        self._strategies[strategy.strategy_id] = strategy
        self._records[strategy.strategy_id] = []
        self._start_times[strategy.strategy_id] = utc_now().timestamp()
        
        logger.info(f"影子策略注册: {strategy.strategy_id}")
    
    def unregister_strategy(self, strategy_id: str) -> None:
        """注销影子策略"""
        self._strategies.pop(strategy_id, None)
        self._records.pop(strategy_id, None)
        self._start_times.pop(strategy_id, None)
        
        logger.info(f"影子策略注销: {strategy_id}")
    
    async def run_all(self, market_data: list[MarketBar]) -> list[ShadowTradeRecord]:
        """
        运行所有 SHADOW 策略
        
        Args:
            market_data: K 线数据
        
        Returns:
            本次生成的影子交易记录
        """
        if not market_data:
            return []
        
        results = []
        current_price = market_data[-1].close
        
        for strategy_id, strategy in self._strategies.items():
            try:
                claim = strategy.run(market_data)
                if claim and claim.direction:
                    record = self._record_trade(strategy_id, claim, current_price)
                    results.append(record)
            except Exception as e:
                logger.error(f"影子策略运行失败: {strategy_id}, {e}")
        
        return results
    
    def _record_trade(
        self,
        strategy_id: str,
        claim: Claim,
        market_price: float,
    ) -> ShadowTradeRecord:
        """记录影子交易"""
        record = ShadowTradeRecord(
            strategy_id=strategy_id,
            claim=claim,
            timestamp=utc_now(),
            market_price=market_price,
            simulated_entry=market_price,
        )
        
        self._records.setdefault(strategy_id, []).append(record)
        
        logger.debug(
            f"影子交易记录: {strategy_id}, 方向: {claim.direction}, 价格: {market_price}",
            extra={"strategy_id": strategy_id, "direction": claim.direction},
        )
        
        return record
    
    def update_trade_result(
        self,
        strategy_id: str,
        exit_price: float,
    ) -> None:
        """
        更新最近一笔影子交易的结果
        
        Args:
            strategy_id: 策略 ID
            exit_price: 退出价格
        """
        records = self._records.get(strategy_id, [])
        if not records:
            return
        
        # 更新最近一笔未结算的交易
        for record in reversed(records):
            if record.simulated_exit is None:
                record.simulated_exit = exit_price
                
                # 计算 PnL
                if record.claim.direction == "long":
                    record.simulated_pnl = (exit_price - record.simulated_entry) / record.simulated_entry
                else:
                    record.simulated_pnl = (record.simulated_entry - exit_price) / record.simulated_entry
                
                break
    
    def get_performance(self, strategy_id: str) -> ShadowPerformance | None:
        """
        获取影子运行绩效
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            绩效统计
        """
        records = self._records.get(strategy_id, [])
        start_time = self._start_times.get(strategy_id)
        
        if not records or not start_time:
            return None
        
        # 只统计已结算的交易
        settled = [r for r in records if r.simulated_pnl is not None]
        
        if not settled:
            return ShadowPerformance(
                strategy_id=strategy_id,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_pnl=0.0,
                win_rate=0.0,
                days_running=int((utc_now().timestamp() - start_time) / 86400),
                first_trade_at=None,
                last_trade_at=None,
            )
        
        winning = [r for r in settled if r.simulated_pnl > 0]
        losing = [r for r in settled if r.simulated_pnl <= 0]
        total_pnl = sum(r.simulated_pnl for r in settled)
        
        return ShadowPerformance(
            strategy_id=strategy_id,
            total_trades=len(settled),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_pnl=total_pnl,
            win_rate=len(winning) / len(settled) if settled else 0.0,
            days_running=int((utc_now().timestamp() - start_time) / 86400),
            first_trade_at=settled[0].timestamp,
            last_trade_at=settled[-1].timestamp,
        )
    
    def is_ready_for_promotion(self, strategy_id: str) -> bool:
        """
        检查是否满足晋升条件
        
        条件：
        - 运行 >= 7 天
        - 胜率 >= 51%
        - 交易数 >= 10
        """
        perf = self.get_performance(strategy_id)
        if not perf:
            return False
        
        return (
            perf.days_running >= MIN_SHADOW_DAYS
            and perf.win_rate >= MIN_WIN_RATE
            and perf.total_trades >= MIN_TRADES
        )
    
    def get_all_performances(self) -> list[ShadowPerformance]:
        """获取所有影子策略绩效"""
        results = []
        for strategy_id in self._strategies:
            perf = self.get_performance(strategy_id)
            if perf:
                results.append(perf)
        return results
    
    def get_records(self, strategy_id: str) -> list[ShadowTradeRecord]:
        """获取影子交易记录"""
        return self._records.get(strategy_id, [])
    
    @property
    def strategy_count(self) -> int:
        """影子策略数量"""
        return len(self._strategies)
