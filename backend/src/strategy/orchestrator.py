"""
BTC 自动交易系统 — 策略编排器

负责证人调度、Claim 聚合、冲突消解和高交易窗口判定。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from src.common.enums import ClaimType, WitnessTier
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar

from .base import BaseStrategy
from .health import HealthManager
from .registry import WitnessRegistry

if TYPE_CHECKING:
    from .lifecycle.weight import WeightManager

logger = get_logger(__name__)


class ConflictResolution(str, Enum):
    """冲突消解结果"""
    NO_CONFLICT = "no_conflict"
    REGIME_UNCLEAR = "regime_unclear"
    VETOED = "vetoed"
    DOMINANT_SELECTED = "dominant_selected"


@dataclass
class AggregatedResult:
    """聚合结果"""
    claims: list[Claim]
    resolution: ConflictResolution
    dominant_claim: Claim | None = None
    veto_claim: Claim | None = None
    total_confidence: float = 0.0
    direction: str | None = None
    is_tradeable: bool = False
    reason: str = ""


@dataclass
class HighTradingWindow:
    """高交易窗口"""
    is_active: bool
    confidence: float
    supporting_witnesses: list[str] = field(default_factory=list)
    direction: str | None = None


class StrategyOrchestrator:
    """
    策略编排器
    
    职责：
    1. 证人调度
    2. Claim 聚合（使用动态权重）
    3. 冲突消解
    4. 高交易窗口判定
    """
    
    # 最小证人数量
    MIN_WITNESSES = 2
    # 核心:辅助比例
    CORE_AUX_RATIO = 2
    # 置信度阈值（默认，可被配置覆盖）
    CONFIDENCE_THRESHOLD = 0.6
    # TIER2 基础因子（默认，可被配置覆盖）
    TIER2_BASE_FACTOR = 0.1
    
    def __init__(
        self,
        registry: WitnessRegistry,
        health_manager: HealthManager,
        weight_manager: "WeightManager | None" = None,
    ):
        self.registry = registry
        self.health_manager = health_manager
        self.weight_manager = weight_manager
        
        # 从配置加载参数
        if weight_manager:
            config = weight_manager.get_aggregation_config()
            self.CONFIDENCE_THRESHOLD = config.get("confidence_threshold", 0.6)
            self.TIER2_BASE_FACTOR = config.get("tier2_base_factor", 0.1)
    
    async def run_witnesses(self, market_data: list[MarketBar]) -> list[Claim]:
        """
        运行所有证人
        
        Args:
            market_data: K 线数据
        
        Returns:
            所有 Claim 列表
        """
        claims: list[Claim] = []
        active_witnesses = self.registry.get_active_witnesses()
        
        for witness in active_witnesses:
            try:
                claim = witness.run(market_data)
                if claim:
                    claims.append(claim)
                    logger.debug(
                        f"证人 {witness.strategy_id} 生成 Claim: {claim.claim_type.value}",
                        extra={"strategy_id": witness.strategy_id, "claim_type": claim.claim_type.value},
                    )
            except Exception as e:
                logger.error(
                    f"证人 {witness.strategy_id} 运行失败: {e}",
                    extra={"strategy_id": witness.strategy_id, "error": str(e)},
                )
        
        return claims
    
    async def aggregate_claims(self, claims: list[Claim]) -> AggregatedResult:
        """
        聚合 Claims
        
        冲突消解规则：
        1. TIER 3 否决 → 立即停止
        2. 两个 TIER 1 范式互斥 → REGIME_UNCLEAR
        3. 选择置信度最高的 TIER 1 作为 DOMINANT
        """
        if not claims:
            return AggregatedResult(
                claims=[],
                resolution=ConflictResolution.NO_CONFLICT,
                is_tradeable=False,
                reason="no_claims",
            )
        
        # 1. 检查 TIER 3 否决
        veto_claims = [c for c in claims if c.claim_type == ClaimType.EXECUTION_VETO]
        if veto_claims:
            return AggregatedResult(
                claims=claims,
                resolution=ConflictResolution.VETOED,
                veto_claim=veto_claims[0],
                is_tradeable=False,
                reason=f"vetoed_by_{veto_claims[0].strategy_id}",
            )
        
        # 2. 分离 TIER 1 和 TIER 2 Claims
        tier1_claims = self._get_tier_claims(claims, WitnessTier.TIER_1)
        tier2_claims = self._get_tier_claims(claims, WitnessTier.TIER_2)
        
        # 3. 检查 TIER 1 冲突
        if len(tier1_claims) >= 2:
            directions = set(c.direction for c in tier1_claims if c.direction)
            if len(directions) > 1:
                # 方向冲突
                return AggregatedResult(
                    claims=claims,
                    resolution=ConflictResolution.REGIME_UNCLEAR,
                    is_tradeable=False,
                    reason="tier1_direction_conflict",
                )
        
        # 4. 选择 DOMINANT
        eligible_claims = [
            c for c in tier1_claims
            if c.claim_type == ClaimType.MARKET_ELIGIBLE
        ]
        
        if not eligible_claims:
            return AggregatedResult(
                claims=claims,
                resolution=ConflictResolution.NO_CONFLICT,
                is_tradeable=False,
                reason="no_eligible_claims",
            )
        
        # 选择置信度最高的
        dominant = max(eligible_claims, key=lambda c: c.confidence)
        
        # 5. 计算总置信度（使用动态权重）
        total_confidence = self._calculate_total_confidence(dominant, tier2_claims)
        
        # 6. 检查是否可交易
        is_tradeable = (
            total_confidence >= self.CONFIDENCE_THRESHOLD
            and dominant.direction is not None
        )
        
        return AggregatedResult(
            claims=claims,
            resolution=ConflictResolution.DOMINANT_SELECTED,
            dominant_claim=dominant,
            total_confidence=total_confidence,
            direction=dominant.direction,
            is_tradeable=is_tradeable,
            reason="dominant_selected" if is_tradeable else "confidence_too_low",
        )
    
    async def check_high_trading_window(self, claims: list[Claim]) -> HighTradingWindow:
        """
        检查高交易窗口
        
        条件：
        1. 至少 2 个证人支持
        2. 核心:辅助比例满足
        3. 方向一致
        """
        if not claims:
            return HighTradingWindow(is_active=False, confidence=0.0)
        
        # 过滤有效 Claims
        valid_claims = [
            c for c in claims
            if c.claim_type in (ClaimType.MARKET_ELIGIBLE, ClaimType.REGIME_MATCHED)
            and c.direction is not None
        ]
        
        if len(valid_claims) < self.MIN_WITNESSES:
            return HighTradingWindow(is_active=False, confidence=0.0)
        
        # 检查方向一致性
        directions = [c.direction for c in valid_claims]
        if len(set(directions)) > 1:
            return HighTradingWindow(is_active=False, confidence=0.0)
        
        direction = directions[0]
        
        # 检查核心:辅助比例
        tier1_count = sum(1 for c in valid_claims if self._is_tier1(c))
        tier2_count = len(valid_claims) - tier1_count
        
        if tier1_count == 0:
            return HighTradingWindow(is_active=False, confidence=0.0)
        
        # 计算置信度（使用动态权重）
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for claim in valid_claims:
            weight = self._get_effective_weight(claim.strategy_id)
            weighted_confidence += claim.confidence * weight
            total_weight += weight
        
        avg_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
        
        return HighTradingWindow(
            is_active=True,
            confidence=avg_confidence,
            supporting_witnesses=[c.strategy_id for c in valid_claims],
            direction=direction,
        )
    
    def _get_tier_claims(self, claims: list[Claim], tier: WitnessTier) -> list[Claim]:
        """获取指定等级的 Claims"""
        result = []
        for claim in claims:
            witness = self.registry.get_witness(claim.strategy_id)
            if witness and witness.tier == tier:
                result.append(claim)
        return result
    
    def _is_tier1(self, claim: Claim) -> bool:
        """检查是否为 TIER 1"""
        witness = self.registry.get_witness(claim.strategy_id)
        return witness is not None and witness.tier == WitnessTier.TIER_1
    
    def _get_effective_weight(self, strategy_id: str) -> float:
        """获取有效权重"""
        if self.weight_manager:
            weight = self.weight_manager.get_weight(strategy_id)
            return weight.effective_weight
        return 1.0
    
    def _calculate_total_confidence(
        self, dominant: Claim, supporting: list[Claim]
    ) -> float:
        """计算总置信度（使用动态权重）"""
        base = dominant.confidence
        
        # 辅助证人加成（使用动态权重）
        for claim in supporting:
            weight = self._get_effective_weight(claim.strategy_id)
            factor = weight * self.TIER2_BASE_FACTOR
            
            if claim.direction == dominant.direction:
                # 同向支持，加成
                base += claim.confidence * factor
            elif claim.direction is not None:
                # 反向，减成
                base -= claim.confidence * factor * 0.5
        
        return min(0.95, max(0.0, base))
