"""
BTC 自动交易系统 — 证人生成器

从假设生成证人，复用 strategy/base.py。
"""

from typing import Any, Callable

from src.common.enums import ClaimType, HypothesisStatus, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar
from src.strategy.base import BaseStrategy
from src.strategy.health import HealthManager
from src.strategy.registry import WitnessRegistry

from ..pool.models import Hypothesis

logger = get_logger(__name__)


class WitnessGenerator:
    """
    证人生成器
    
    从验证通过的假设生成证人类，注册到 WitnessRegistry。
    """
    
    def __init__(
        self,
        registry: WitnessRegistry,
        health_manager: HealthManager,
    ):
        self.registry = registry
        self.health_manager = health_manager

    def generate_witness_class(
        self,
        hypothesis: Hypothesis,
    ) -> type[BaseStrategy]:
        """
        从假设生成证人类
        
        Args:
            hypothesis: 假设
        
        Returns:
            证人类（继承 BaseStrategy）
        """
        tier = self._map_tier(hypothesis.status)
        event_checker = self._compile_event_checker(hypothesis)
        
        # 捕获假设引用
        hyp = hypothesis
        
        class GeneratedWitness(BaseStrategy):
            """由假设工厂生成的证人"""
            
            def __init__(self) -> None:
                super().__init__(
                    strategy_id=f"hyp_{hyp.id}",
                    tier=tier,
                    validity_window=60,
                )
                self._hypothesis = hyp
                self._event_checker = event_checker
            
            def generate_claim(self, market_data: list[MarketBar]) -> Claim | None:
                """生成策略声明"""
                if not market_data:
                    return None
                
                # 检查事件条件
                if self._event_checker(market_data):
                    direction = self._determine_direction(market_data)
                    return self.create_claim(
                        claim_type=ClaimType.MARKET_ELIGIBLE,
                        confidence=0.6,
                        direction=direction,
                    )
                return None
            
            def _determine_direction(self, data: list[MarketBar]) -> str:
                """确定方向"""
                expected = self._hypothesis.expected_direction
                if expected == "breakout":
                    # 跟随突破方向
                    if len(data) >= 2:
                        return "long" if data[-1].close > data[-2].close else "short"
                    return "long"
                elif expected == "trend":
                    # 跟随趋势
                    if len(data) >= 5:
                        return "long" if data[-1].close > data[-5].close else "short"
                    return "long"
                return expected if expected in ("long", "short") else "long"
        
        return GeneratedWitness

    def generate_and_register(self, hypothesis: Hypothesis) -> BaseStrategy | None:
        """
        生成证人并注册
        
        Args:
            hypothesis: 假设
        
        Returns:
            证人实例，失败返回 None
        """
        if not hypothesis.is_promotable:
            logger.warning(f"假设不可晋升: {hypothesis.id}, status={hypothesis.status}")
            return None
        
        try:
            # 生成证人类
            witness_class = self.generate_witness_class(hypothesis)
            witness = witness_class()
            
            # 注册
            self.registry.register(witness)
            self.health_manager.initialize_health(witness)
            
            # 更新假设状态
            hypothesis.update_status(HypothesisStatus.PROMOTED)
            
            logger.info(
                f"证人已生成并注册: {witness.strategy_id}, tier={witness.tier.value}",
                extra={"witness_id": witness.strategy_id, "tier": witness.tier.value},
            )
            
            return witness
        
        except Exception as e:
            logger.error(f"生成证人失败: {hypothesis.id}, error={e}")
            return None
    
    def _map_tier(self, status: HypothesisStatus) -> WitnessTier:
        """映射假设状态到证人等级"""
        mapping = {
            HypothesisStatus.TIER_1: WitnessTier.TIER_1,
            HypothesisStatus.TIER_2: WitnessTier.TIER_2,
            HypothesisStatus.TIER_3: WitnessTier.TIER_3,
        }
        return mapping.get(status, WitnessTier.TIER_2)
    
    def _compile_event_checker(
        self,
        hypothesis: Hypothesis,
    ) -> Callable[[list[MarketBar]], bool]:
        """
        编译事件检查器
        
        根据假设的事件定义生成检查函数。
        """
        event_type = hypothesis.source_detector
        params = hypothesis.event_params
        
        if event_type == "volatility":
            return self._create_volatility_checker(params)
        
        # 默认：总是返回 False
        return lambda data: False
    
    def _create_volatility_checker(
        self,
        params: dict[str, float],
    ) -> Callable[[list[MarketBar]], bool]:
        """创建波动率检查器"""
        compression_threshold = params.get("compression_threshold", 0.5)
        release_threshold = params.get("release_threshold", 2.0)
        lookback = int(params.get("lookback_period", 20))
        
        def checker(data: list[MarketBar]) -> bool:
            if len(data) < lookback + 100:
                return False
            
            # 计算 ATR
            atr_values = []
            for i in range(lookback, len(data)):
                tr_sum = 0.0
                for j in range(i - lookback + 1, i + 1):
                    high = data[j].high
                    low = data[j].low
                    prev_close = data[j - 1].close
                    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                    tr_sum += tr
                atr_values.append(tr_sum / lookback)
            
            if len(atr_values) < 100:
                return False
            
            avg_atr = sum(atr_values[-101:-1]) / 100
            current_atr = atr_values[-1]
            
            if avg_atr == 0:
                return False
            
            ratio = current_atr / avg_atr
            
            # 检测压缩或释放
            return ratio < compression_threshold or ratio > release_threshold
        
        return checker
