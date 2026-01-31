"""
BTC 自动交易系统 — 证人注册表

管理证人的注册、注销和查询。
"""

from src.common.enums import StrategyStatus, WitnessTier
from src.common.logging import get_logger

from .base import BaseStrategy

logger = get_logger(__name__)


# TIER_3 保护列表（不可降级）
PROTECTED_WITNESSES = {"risk_sentinel", "macro_sentinel"}


class WitnessRegistry:
    """
    证人注册表
    
    管理所有证人的注册和查询。
    支持动态状态和 TIER 管理。
    """
    
    def __init__(self):
        self._witnesses: dict[str, BaseStrategy] = {}
        self._status: dict[str, StrategyStatus] = {}
        self._tier_overrides: dict[str, WitnessTier] = {}  # 动态 TIER 覆盖
    
    def register(self, witness: BaseStrategy) -> None:
        """
        注册证人
        
        Args:
            witness: 证人实例
        """
        if witness.strategy_id in self._witnesses:
            logger.warning(f"证人已存在，将被覆盖: {witness.strategy_id}")
        
        self._witnesses[witness.strategy_id] = witness
        self._status[witness.strategy_id] = StrategyStatus.ACTIVE
        logger.info(
            f"证人已注册: {witness.strategy_id}, 等级: {witness.tier.value}",
            extra={"strategy_id": witness.strategy_id, "tier": witness.tier.value},
        )
    
    def unregister(self, strategy_id: str) -> bool:
        """
        注销证人
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            是否成功
        """
        if strategy_id in self._witnesses:
            del self._witnesses[strategy_id]
            self._status.pop(strategy_id, None)
            self._tier_overrides.pop(strategy_id, None)
            logger.info(f"证人已注销: {strategy_id}")
            return True
        return False
    
    def get_witness(self, strategy_id: str) -> BaseStrategy | None:
        """获取证人"""
        return self._witnesses.get(strategy_id)
    
    def get_all_witnesses(self) -> list[BaseStrategy]:
        """获取所有证人"""
        return list(self._witnesses.values())
    
    def get_active_witnesses(self) -> list[BaseStrategy]:
        """获取所有激活的证人"""
        return [w for w in self._witnesses.values() if w.is_active]
    
    def get_by_tier(self, tier: WitnessTier) -> list[BaseStrategy]:
        """
        按等级获取证人
        
        Args:
            tier: 证人等级
        
        Returns:
            证人列表
        """
        return [w for w in self._witnesses.values() if w.tier == tier]
    
    def get_core_witnesses(self) -> list[BaseStrategy]:
        """获取核心证人（TIER 1）"""
        return self.get_by_tier(WitnessTier.TIER_1)
    
    def get_auxiliary_witnesses(self) -> list[BaseStrategy]:
        """获取辅助证人（TIER 2）"""
        return self.get_by_tier(WitnessTier.TIER_2)
    
    def get_veto_witnesses(self) -> list[BaseStrategy]:
        """获取否决证人（TIER 3）"""
        return self.get_by_tier(WitnessTier.TIER_3)
    
    @property
    def count(self) -> int:
        """证人总数"""
        return len(self._witnesses)
    
    @property
    def active_count(self) -> int:
        """激活证人数"""
        return len(self.get_active_witnesses())
    
    # === 状态管理 ===
    
    def get_status(self, strategy_id: str) -> StrategyStatus | None:
        """获取证人状态"""
        return self._status.get(strategy_id)
    
    def set_status(self, strategy_id: str, status: StrategyStatus) -> bool:
        """
        设置证人状态
        
        Args:
            strategy_id: 策略 ID
            status: 新状态
        
        Returns:
            是否成功
        """
        if strategy_id not in self._witnesses:
            return False
        
        old_status = self._status.get(strategy_id)
        self._status[strategy_id] = status
        
        logger.info(
            f"证人状态变更: {strategy_id}, {old_status} -> {status.value}",
            extra={"strategy_id": strategy_id, "old": old_status, "new": status.value},
        )
        return True
    
    def get_by_status(self, status: StrategyStatus) -> list[BaseStrategy]:
        """按状态获取证人"""
        return [
            w for w in self._witnesses.values()
            if self._status.get(w.strategy_id) == status
        ]
    
    # === TIER 管理 ===
    
    def get_tier(self, strategy_id: str) -> WitnessTier | None:
        """获取证人 TIER（优先返回覆盖值）"""
        if strategy_id in self._tier_overrides:
            return self._tier_overrides[strategy_id]
        witness = self._witnesses.get(strategy_id)
        return witness.tier if witness else None
    
    def set_tier(self, strategy_id: str, tier: WitnessTier) -> bool:
        """
        设置证人 TIER（动态覆盖）
        
        Args:
            strategy_id: 策略 ID
            tier: 新 TIER
        
        Returns:
            是否成功
        """
        if strategy_id not in self._witnesses:
            return False
        
        if self.is_protected(strategy_id):
            logger.warning(f"受保护证人不可修改 TIER: {strategy_id}")
            return False
        
        old_tier = self.get_tier(strategy_id)
        self._tier_overrides[strategy_id] = tier
        
        logger.info(
            f"证人 TIER 变更: {strategy_id}, {old_tier} -> {tier.value}",
            extra={"strategy_id": strategy_id, "old": old_tier, "new": tier.value},
        )
        return True
    
    def is_protected(self, strategy_id: str) -> bool:
        """
        检查证人是否受保护（TIER_3 否决证人）
        
        受保护证人不可降级或废弃。
        """
        witness = self._witnesses.get(strategy_id)
        if not witness:
            return False
        
        # TIER_3 证人受保护
        if witness.tier == WitnessTier.TIER_3:
            return True
        
        # 特定证人受保护
        return strategy_id in PROTECTED_WITNESSES
