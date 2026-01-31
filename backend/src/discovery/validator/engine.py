"""
BTC 自动交易系统 — 假设验证引擎

复用 learning/statistics.py 进行统计验证。
"""

import math
import statistics as stats

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.learning.collector import TradeData
from src.learning.statistics import StatisticsAnalyzer

from ..pool.models import Hypothesis, ValidationResult

logger = get_logger(__name__)


# 验证阈值
VALIDATION_THRESHOLDS = {
    "tier_1": {"p_value": 0.05, "win_rate": 0.52, "cohens_d": 0.3},
    "tier_2": {"p_value": 0.20, "win_rate": 0.51, "cohens_d": 0.2},
    "tier_3": {"p_value": 0.30, "win_rate": 0.50, "cohens_d": 0.1},
}

MIN_SAMPLE_SIZE = 100


class HypothesisValidator:
    """
    假设验证器
    
    复用 StatisticsAnalyzer 进行统计验证。
    """
    
    def __init__(self):
        self.stats = StatisticsAnalyzer()

    async def validate(
        self,
        hypothesis: Hypothesis,
        trades: list[TradeData],
    ) -> ValidationResult:
        """
        验证假设
        
        Args:
            hypothesis: 假设
            trades: 交易数据
        
        Returns:
            验证结果
        """
        sample_size = len(trades)
        
        if sample_size < MIN_SAMPLE_SIZE:
            logger.warning(f"样本量不足: {sample_size} < {MIN_SAMPLE_SIZE}")
            return ValidationResult(
                p_value=1.0,
                win_rate=0.0,
                cohens_d=0.0,
                sample_size=sample_size,
                is_robust=False,
                correlation_max=0.0,
            )
        
        # 复用 StatisticsAnalyzer
        pnl_stats = self.stats.calculate_pnl_statistics(trades)
        sharpe = self.stats.calculate_sharpe_ratio(trades)
        
        # 计算 p-value（简化：基于胜率的二项检验）
        p_value = self._calculate_p_value(pnl_stats.win_count, sample_size)
        
        # 计算 Cohen's d
        cohens_d = self._calculate_cohens_d(trades)
        
        # 鲁棒性检验（简化）
        is_robust = self._check_robustness(pnl_stats.win_rate, sample_size)
        
        result = ValidationResult(
            p_value=p_value,
            win_rate=pnl_stats.win_rate,
            cohens_d=cohens_d,
            sample_size=sample_size,
            is_robust=is_robust,
            correlation_max=0.0,
            sharpe_ratio=sharpe,
            profit_factor=pnl_stats.profit_factor,
        )
        
        logger.info(
            f"假设验证完成: {hypothesis.id}, p={p_value:.4f}, win_rate={pnl_stats.win_rate:.2%}",
            extra={"hypothesis_id": hypothesis.id, "p_value": p_value, "win_rate": pnl_stats.win_rate},
        )
        
        return result

    def determine_tier(self, result: ValidationResult) -> HypothesisStatus:
        """
        根据验证结果判定等级
        
        Args:
            result: 验证结果
        
        Returns:
            假设状态（TIER_1/TIER_2/TIER_3/FAIL）
        """
        if result.sample_size < MIN_SAMPLE_SIZE:
            return HypothesisStatus.FAIL
        
        if not result.is_robust:
            return HypothesisStatus.FAIL
        
        # TIER_1: p < 0.05, win_rate >= 52%, Cohen's d > 0.3
        t1 = VALIDATION_THRESHOLDS["tier_1"]
        if (result.p_value < t1["p_value"] and 
            result.win_rate >= t1["win_rate"] and 
            result.cohens_d > t1["cohens_d"]):
            return HypothesisStatus.TIER_1
        
        # TIER_2: p < 0.20, win_rate >= 51%, Cohen's d > 0.2
        t2 = VALIDATION_THRESHOLDS["tier_2"]
        if (result.p_value < t2["p_value"] and 
            result.win_rate >= t2["win_rate"] and 
            result.cohens_d > t2["cohens_d"]):
            return HypothesisStatus.TIER_2
        
        # TIER_3: p < 0.30, win_rate >= 50%, Cohen's d > 0.1
        t3 = VALIDATION_THRESHOLDS["tier_3"]
        if (result.p_value < t3["p_value"] and 
            result.win_rate >= t3["win_rate"] and 
            result.cohens_d > t3["cohens_d"]):
            return HypothesisStatus.TIER_3
        
        return HypothesisStatus.FAIL
    
    def check_correlation(
        self,
        hypothesis: Hypothesis,
        existing_witness_signals: dict[str, list[bool]],
        hypothesis_signals: list[bool],
    ) -> float:
        """
        检查与现有证人的相关性
        
        Args:
            hypothesis: 假设
            existing_witness_signals: 现有证人信号 {witness_id: [signals]}
            hypothesis_signals: 假设信号
        
        Returns:
            最大相关性
        """
        if not existing_witness_signals or not hypothesis_signals:
            return 0.0
        
        max_corr = 0.0
        for witness_id, signals in existing_witness_signals.items():
            if len(signals) != len(hypothesis_signals):
                continue
            corr = self._calculate_correlation(signals, hypothesis_signals)
            hypothesis.correlation_with_existing[witness_id] = corr
            max_corr = max(max_corr, abs(corr))
        
        return max_corr

    def _calculate_p_value(self, wins: int, total: int) -> float:
        """计算 p-value（二项检验，H0: p=0.5）"""
        if total == 0:
            return 1.0
        
        # 简化：使用正态近似
        p0 = 0.5
        p_hat = wins / total
        se = math.sqrt(p0 * (1 - p0) / total)
        
        if se == 0:
            return 1.0
        
        z = (p_hat - p0) / se
        
        # 单侧检验（胜率 > 50%）
        # 使用标准正态分布近似
        p_value = 1 - self._normal_cdf(z)
        return p_value
    
    def _calculate_cohens_d(self, trades: list[TradeData]) -> float:
        """计算 Cohen's d 效应量"""
        if len(trades) < 2:
            return 0.0
        
        pnls = [t.pnl for t in trades]
        mean_pnl = stats.mean(pnls)
        std_pnl = stats.stdev(pnls)
        
        if std_pnl == 0:
            return 0.0
        
        # Cohen's d = (mean - 0) / std
        return mean_pnl / std_pnl
    
    def _check_robustness(self, win_rate: float, sample_size: int) -> bool:
        """检查鲁棒性（简化版）"""
        # 样本量足够且胜率稳定
        if sample_size < MIN_SAMPLE_SIZE:
            return False
        
        # 胜率在合理范围内
        if win_rate < 0.48 or win_rate > 0.65:
            return False
        
        return True
    
    def _calculate_correlation(
        self,
        signals_a: list[bool],
        signals_b: list[bool],
    ) -> float:
        """计算两个信号序列的相关性"""
        if len(signals_a) != len(signals_b) or len(signals_a) < 2:
            return 0.0
        
        a = [1.0 if s else 0.0 for s in signals_a]
        b = [1.0 if s else 0.0 for s in signals_b]
        
        mean_a = stats.mean(a)
        mean_b = stats.mean(b)
        
        numerator = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(len(a)))
        
        var_a = sum((x - mean_a) ** 2 for x in a)
        var_b = sum((x - mean_b) ** 2 for x in b)
        
        denominator = math.sqrt(var_a * var_b)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _normal_cdf(self, z: float) -> float:
        """标准正态分布 CDF（近似）"""
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))
