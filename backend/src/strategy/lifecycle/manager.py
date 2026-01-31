"""
BTC 自动交易系统 — 策略池管理器

统一管理策略生命周期：NEW → TESTING → SHADOW → ACTIVE → DEGRADED → RETIRED
"""

from datetime import timedelta
from typing import TYPE_CHECKING

from src.common.enums import HealthGrade, HypothesisStatus, StrategyStatus, WitnessTier
from src.common.logging import get_logger
from src.common.utils import utc_now
from src.discovery.pool.manager import HypothesisPoolManager
from src.discovery.promoter.generator import WitnessGenerator
from src.discovery.validator.engine import HypothesisValidator

from ..health import HealthManager
from ..registry import WitnessRegistry
from .models import StrategyStateRecord
from .storage import LifecycleStorage
from .weight import WeightManager

if TYPE_CHECKING:
    from .shadow import ShadowRunner

logger = get_logger(__name__)


# 晋升条件
SHADOW_MIN_DAYS = 7  # 影子运行最少天数
SHADOW_MIN_WIN_RATE = 0.51  # 影子运行最低胜率
TIER1_UPGRADE_DAYS = 30  # 升级 TIER_1 最少运行天数
TIER1_UPGRADE_GRADE = HealthGrade.A  # 升级 TIER_1 需要健康度 A

# 降级条件
DEGRADED_GRADE = HealthGrade.D  # 降级触发等级
RETIRED_DAYS = 30  # 废弃后保留天数


class StrategyPoolManager:
    """
    策略池管理器
    
    整合 HypothesisPoolManager 和 WitnessRegistry，
    提供统一的策略生命周期管理。
    """
    
    def __init__(
        self,
        hypothesis_pool: HypothesisPoolManager,
        registry: WitnessRegistry,
        health_manager: HealthManager,
        weight_manager: WeightManager,
        validator: HypothesisValidator | None = None,
        shadow_runner: "ShadowRunner | None" = None,
        storage: LifecycleStorage | None = None,
        witness_generator: WitnessGenerator | None = None,
    ):
        self.hypothesis_pool = hypothesis_pool
        self.registry = registry
        self.health_manager = health_manager
        self.weight_manager = weight_manager
        self.validator = validator
        self.shadow_runner = shadow_runner
        self.storage = storage or LifecycleStorage()
        self.witness_generator = witness_generator or WitnessGenerator(registry, health_manager)
        
        # 从存储加载状态
        self._state_history: list[StrategyStateRecord] = self.storage.load_state_history()
        self._shadow_start_times: dict[str, float] = self.storage.load_shadow_times()
    
    def set_shadow_runner(self, runner: "ShadowRunner") -> None:
        """设置影子运行器（延迟注入）"""
        self.shadow_runner = runner
    
    # === 状态查询 ===
    
    def get_status(self, strategy_id: str) -> StrategyStatus | None:
        """获取策略状态"""
        # 先查 registry（已激活的证人）
        status = self.registry.get_status(strategy_id)
        if status:
            return status
        
        # 检查是否在 SHADOW 运行中
        if strategy_id in self._shadow_start_times:
            return StrategyStatus.SHADOW
        
        return None
    
    async def get_status_async(self, strategy_id: str) -> StrategyStatus | None:
        """异步获取策略状态（包含 hypothesis_pool 查询）"""
        # 先查 registry
        status = self.registry.get_status(strategy_id)
        if status:
            return status
        
        # 检查 SHADOW
        if strategy_id in self._shadow_start_times:
            return StrategyStatus.SHADOW
        
        # 查 hypothesis_pool
        hypothesis = await self.hypothesis_pool.get(strategy_id)
        if hypothesis:
            if hypothesis.status == HypothesisStatus.NEW:
                return StrategyStatus.NEW
            elif hypothesis.status == HypothesisStatus.VALIDATING:
                return StrategyStatus.TESTING
        
        return None
    
    def get_all_by_status(self, status: StrategyStatus) -> list[str]:
        """按状态获取所有策略 ID"""
        result = []
        
        # 从 registry 获取
        for witness in self.registry.get_by_status(status):
            result.append(witness.strategy_id)
        
        return result
    
    def get_state_history(self, strategy_id: str) -> list[StrategyStateRecord]:
        """获取策略状态变更历史"""
        return [r for r in self._state_history if r.strategy_id == strategy_id]
    
    # === 晋升逻辑 ===
    
    async def promote(self, strategy_id: str, by: str = "system") -> bool:
        """
        统一晋升入口
        
        根据当前状态自动选择下一阶段：
        - NEW → TESTING
        - TESTING → SHADOW
        - SHADOW → ACTIVE (TIER_2)
        - DEGRADED → ACTIVE
        """
        current = self.get_status(strategy_id)
        
        if current == StrategyStatus.NEW:
            return await self._promote_to_testing(strategy_id, by)
        elif current == StrategyStatus.TESTING:
            return await self._promote_to_shadow(strategy_id, by)
        elif current == StrategyStatus.SHADOW:
            return await self._promote_to_active(strategy_id, by)
        elif current == StrategyStatus.DEGRADED:
            return await self._restore_to_active(strategy_id, by)
        
        logger.warning(f"无法晋升: {strategy_id}, 当前状态: {current}")
        return False
    
    async def _promote_to_testing(self, strategy_id: str, by: str) -> bool:
        """NEW → TESTING"""
        hypothesis = await self.hypothesis_pool.get(strategy_id)
        if not hypothesis:
            return False
        
        await self.hypothesis_pool.update_status(strategy_id, HypothesisStatus.VALIDATING)
        self._record_state_change(strategy_id, StrategyStatus.TESTING, StrategyStatus.NEW, None, "进入回测验证", by)
        
        logger.info(f"策略晋升到 TESTING: {strategy_id}")
        return True
    
    async def _promote_to_shadow(self, strategy_id: str, by: str) -> bool:
        """TESTING → SHADOW"""
        hypothesis = await self.hypothesis_pool.get(strategy_id)
        if not hypothesis:
            return False
        
        # 检查验证结果
        if not hypothesis.is_promotable:
            logger.warning(f"假设验证未通过: {strategy_id}")
            return False
        
        await self.hypothesis_pool.promote_to_shadow(strategy_id)
        self._shadow_start_times[strategy_id] = utc_now().timestamp()
        self._save_shadow_times()
        self._record_state_change(strategy_id, StrategyStatus.SHADOW, StrategyStatus.TESTING, None, "进入影子运行", by)
        
        logger.info(f"策略晋升到 SHADOW: {strategy_id}")
        return True
    
    async def _promote_to_active(self, strategy_id: str, by: str) -> bool:
        """SHADOW → ACTIVE (默认 TIER_2)"""
        # 检查影子运行条件
        if not self._check_shadow_promotion(strategy_id):
            logger.warning(f"影子运行条件不满足: {strategy_id}")
            return False
        
        # 获取假设
        hypothesis = await self.hypothesis_pool.get(strategy_id)
        if not hypothesis:
            logger.warning(f"假设不存在: {strategy_id}")
            return False
        
        # 生成并注册证人
        witness = self.witness_generator.generate_and_register(hypothesis)
        if not witness:
            logger.error(f"证人生成失败: {strategy_id}")
            return False
        
        # 设置状态和 TIER
        self.registry.set_status(witness.strategy_id, StrategyStatus.ACTIVE)
        self.registry.set_tier(witness.strategy_id, WitnessTier.TIER_2)
        
        # 从 shadow 池移除
        await self.hypothesis_pool.remove_from_shadow(strategy_id)
        self._shadow_start_times.pop(strategy_id, None)
        self._save_shadow_times()
        
        self._record_state_change(witness.strategy_id, StrategyStatus.ACTIVE, StrategyStatus.SHADOW, WitnessTier.TIER_2, "晋升为正式证人", by)
        
        logger.info(f"策略晋升到 ACTIVE (TIER_2): {witness.strategy_id}")
        return True
    
    async def _restore_to_active(self, strategy_id: str, by: str) -> bool:
        """DEGRADED → ACTIVE"""
        # 检查健康度是否恢复
        health = self.health_manager.get_health(strategy_id)
        if not health or health.grade in (HealthGrade.C, HealthGrade.D):
            logger.warning(f"健康度未恢复: {strategy_id}")
            return False
        
        self.registry.set_status(strategy_id, StrategyStatus.ACTIVE)
        tier = self.registry.get_tier(strategy_id)
        self._record_state_change(strategy_id, StrategyStatus.ACTIVE, StrategyStatus.DEGRADED, tier, "健康度恢复", by)
        
        logger.info(f"策略恢复到 ACTIVE: {strategy_id}")
        return True
    
    def _check_shadow_promotion(self, strategy_id: str) -> bool:
        """检查影子运行晋升条件"""
        start_time = self._shadow_start_times.get(strategy_id)
        if not start_time:
            return False
        
        # 检查运行天数
        days = (utc_now().timestamp() - start_time) / 86400
        if days < SHADOW_MIN_DAYS:
            return False
        
        # 检查 ShadowRunner 绩效
        if self.shadow_runner:
            return self.shadow_runner.is_ready_for_promotion(strategy_id)
        
        # 无 ShadowRunner 时仅检查天数
        return True
    
    # === TIER 升级 ===
    
    async def upgrade_tier(self, strategy_id: str, by: str = "admin") -> bool:
        """
        TIER_2 → TIER_1（需人工审批）
        
        条件：
        - 运行 >= 30 天
        - 健康度 A
        """
        witness = self.registry.get_witness(strategy_id)
        if not witness:
            return False
        
        current_tier = self.registry.get_tier(strategy_id)
        if current_tier != WitnessTier.TIER_2:
            logger.warning(f"只有 TIER_2 可升级: {strategy_id}, 当前: {current_tier}")
            return False
        
        # 检查健康度
        health = self.health_manager.get_health(strategy_id)
        if not health or health.grade != TIER1_UPGRADE_GRADE:
            logger.warning(f"健康度不满足升级条件: {strategy_id}, 等级: {health.grade if health else 'N/A'}")
            return False
        
        # 升级
        self.registry.set_tier(strategy_id, WitnessTier.TIER_1)
        self._record_state_change(strategy_id, StrategyStatus.ACTIVE, StrategyStatus.ACTIVE, WitnessTier.TIER_1, "升级为核心证人", by)
        
        logger.info(f"策略升级到 TIER_1: {strategy_id}")
        return True
    
    # === 降级逻辑 ===
    
    async def demote(self, strategy_id: str, by: str = "system") -> bool:
        """
        降级策略
        
        ACTIVE → DEGRADED
        """
        if self.registry.is_protected(strategy_id):
            logger.warning(f"受保护策略不可降级: {strategy_id}")
            return False
        
        current = self.registry.get_status(strategy_id)
        if current != StrategyStatus.ACTIVE:
            return False
        
        self.registry.set_status(strategy_id, StrategyStatus.DEGRADED)
        tier = self.registry.get_tier(strategy_id)
        self._record_state_change(strategy_id, StrategyStatus.DEGRADED, current, tier, "健康度下降", by)
        
        logger.info(f"策略降级到 DEGRADED: {strategy_id}")
        return True
    
    async def retire(self, strategy_id: str, by: str = "system") -> bool:
        """
        废弃策略
        
        DEGRADED → RETIRED
        """
        if self.registry.is_protected(strategy_id):
            logger.warning(f"受保护策略不可废弃: {strategy_id}")
            return False
        
        current = self.registry.get_status(strategy_id)
        if current not in (StrategyStatus.DEGRADED, StrategyStatus.ACTIVE):
            return False
        
        self.registry.set_status(strategy_id, StrategyStatus.RETIRED)
        tier = self.registry.get_tier(strategy_id)
        self._record_state_change(strategy_id, StrategyStatus.RETIRED, current, tier, "策略废弃", by)
        
        logger.info(f"策略废弃: {strategy_id}")
        return True
    
    async def check_demotions(self) -> list[str]:
        """
        自动降级检查
        
        检查所有 ACTIVE 策略，健康度 D 自动降级
        """
        demoted = []
        
        for witness in self.registry.get_by_status(StrategyStatus.ACTIVE):
            health = self.health_manager.get_health(witness.strategy_id)
            if health and health.grade == DEGRADED_GRADE:
                if await self.demote(witness.strategy_id):
                    demoted.append(witness.strategy_id)
        
        return demoted
    
    async def cleanup_retired(self, days: int = RETIRED_DAYS) -> int:
        """清理过期废弃策略"""
        cutoff = utc_now() - timedelta(days=days)
        cleaned = 0
        
        for record in self._state_history:
            if record.status == StrategyStatus.RETIRED.value and record.changed_at < cutoff:
                self.registry.unregister(record.strategy_id)
                cleaned += 1
        
        if cleaned:
            logger.info(f"清理废弃策略: {cleaned} 个")
        
        return cleaned
    
    # === 辅助方法 ===
    
    def _record_state_change(
        self,
        strategy_id: str,
        status: StrategyStatus,
        previous: StrategyStatus | None,
        tier: WitnessTier | None,
        reason: str,
        by: str,
    ) -> None:
        """记录状态变更（含持久化）"""
        record = StrategyStateRecord(
            strategy_id=strategy_id,
            status=status.value,
            previous_status=previous.value if previous else None,
            tier=tier,
            changed_at=utc_now(),
            reason=reason,
            changed_by=by,
        )
        self._state_history.append(record)
        
        # 持久化
        self.storage.append_state_record(record)
    
    def _save_shadow_times(self) -> None:
        """保存影子运行时间"""
        self.storage.save_shadow_times(self._shadow_start_times)
