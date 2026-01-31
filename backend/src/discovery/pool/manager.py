"""
BTC 自动交易系统 — 假设候选池管理器

管理假设的生命周期：添加、查询、状态更新、清理。
"""

from datetime import datetime, timedelta

from src.common.enums import HypothesisStatus, StrategyStatus
from src.common.logging import get_logger
from src.common.utils import utc_now

from .models import Hypothesis

logger = get_logger(__name__)


# 资源限制
MAX_HYPOTHESES = 100
MAX_DAILY_GENERATION = 10


class HypothesisPoolManager:
    """
    假设候选池管理器
    
    管理假设的完整生命周期。
    支持 SHADOW 状态用于影子运行。
    """
    
    def __init__(self, max_size: int = MAX_HYPOTHESES):
        self._hypotheses: dict[str, Hypothesis] = {}
        self._max_size = max_size
        self._daily_count: dict[str, int] = {}  # date_str -> count
        self._shadow_hypotheses: dict[str, Hypothesis] = {}  # 影子运行中的假设
    
    async def add(self, hypothesis: Hypothesis) -> bool:
        """
        添加假设到候选池
        
        Args:
            hypothesis: 假设对象
        
        Returns:
            是否成功添加
        """
        # 检查容量
        if len(self._hypotheses) >= self._max_size:
            logger.warning(f"候选池已满，无法添加: {hypothesis.id}")
            return False
        
        # 检查每日限制
        today = utc_now().strftime("%Y-%m-%d")
        daily_count = self._daily_count.get(today, 0)
        if daily_count >= MAX_DAILY_GENERATION:
            logger.warning(f"今日生成已达上限: {daily_count}")
            return False
        
        # 检查重复
        if hypothesis.id in self._hypotheses:
            logger.warning(f"假设已存在: {hypothesis.id}")
            return False
        
        self._hypotheses[hypothesis.id] = hypothesis
        self._daily_count[today] = daily_count + 1
        
        logger.info(
            f"假设已添加: {hypothesis.id}, 来源: {hypothesis.source_detector}",
            extra={"hypothesis_id": hypothesis.id, "detector": hypothesis.source_detector},
        )
        return True
    
    async def get(self, hypothesis_id: str) -> Hypothesis | None:
        """获取假设"""
        return self._hypotheses.get(hypothesis_id)
    
    async def update_status(
        self,
        hypothesis_id: str,
        status: HypothesisStatus,
    ) -> bool:
        """
        更新假设状态
        
        Args:
            hypothesis_id: 假设 ID
            status: 新状态
        
        Returns:
            是否成功
        """
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            logger.warning(f"假设不存在: {hypothesis_id}")
            return False
        
        old_status = hypothesis.status
        hypothesis.update_status(status)
        
        logger.info(
            f"假设状态更新: {hypothesis_id}, {old_status.value} -> {status.value}",
            extra={"hypothesis_id": hypothesis_id, "old": old_status.value, "new": status.value},
        )
        return True
    
    async def get_by_status(self, status: HypothesisStatus) -> list[Hypothesis]:
        """按状态获取假设列表"""
        return [h for h in self._hypotheses.values() if h.status == status]
    
    async def get_all(self) -> list[Hypothesis]:
        """获取所有假设"""
        return list(self._hypotheses.values())
    
    async def get_promotable(self) -> list[Hypothesis]:
        """获取可晋升的假设（TIER_1 或 TIER_2）"""
        return [h for h in self._hypotheses.values() if h.is_promotable]
    
    async def get_pending_validation(self) -> list[Hypothesis]:
        """获取待验证的假设"""
        return await self.get_by_status(HypothesisStatus.NEW)
    
    async def remove(self, hypothesis_id: str) -> bool:
        """移除假设"""
        if hypothesis_id in self._hypotheses:
            del self._hypotheses[hypothesis_id]
            logger.info(f"假设已移除: {hypothesis_id}")
            return True
        return False
    
    async def cleanup_old(self, days: int = 30) -> int:
        """
        清理过期假设
        
        Args:
            days: 保留天数
        
        Returns:
            清理数量
        """
        cutoff = utc_now() - timedelta(days=days)
        to_remove = []
        
        for h_id, h in self._hypotheses.items():
            # 清理失败/废弃的旧假设
            if h.status in (HypothesisStatus.FAIL, HypothesisStatus.DEPRECATED):
                if h.updated_at < cutoff:
                    to_remove.append(h_id)
        
        for h_id in to_remove:
            del self._hypotheses[h_id]
        
        if to_remove:
            logger.info(f"清理过期假设: {len(to_remove)} 个")
        
        return len(to_remove)
    
    async def cleanup_daily_counts(self) -> None:
        """清理过期的每日计数"""
        today = utc_now().strftime("%Y-%m-%d")
        self._daily_count = {k: v for k, v in self._daily_count.items() if k == today}
    
    @property
    def count(self) -> int:
        """假设总数"""
        return len(self._hypotheses)
    
    @property
    def capacity_remaining(self) -> int:
        """剩余容量"""
        return self._max_size - len(self._hypotheses)
    
    def get_statistics(self) -> dict[str, int]:
        """获取统计信息"""
        stats: dict[str, int] = {}
        for h in self._hypotheses.values():
            status = h.status.value
            stats[status] = stats.get(status, 0) + 1
        stats["total"] = len(self._hypotheses)
        stats["shadow"] = len(self._shadow_hypotheses)
        return stats
    
    # === SHADOW 状态支持 ===
    
    async def get_shadow_hypotheses(self) -> list[Hypothesis]:
        """获取所有影子运行中的假设"""
        return list(self._shadow_hypotheses.values())
    
    async def promote_to_shadow(self, hypothesis_id: str) -> bool:
        """
        晋升假设到 SHADOW 状态
        
        条件：假设必须是 TIER_1 或 TIER_2
        
        Args:
            hypothesis_id: 假设 ID
        
        Returns:
            是否成功
        """
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            logger.warning(f"假设不存在: {hypothesis_id}")
            return False
        
        # 检查是否可晋升
        if not hypothesis.is_promotable:
            logger.warning(f"假设不可晋升到 SHADOW: {hypothesis_id}, 状态: {hypothesis.status.value}")
            return False
        
        # 移动到 shadow 池
        self._shadow_hypotheses[hypothesis_id] = hypothesis
        
        logger.info(
            f"假设晋升到 SHADOW: {hypothesis_id}",
            extra={"hypothesis_id": hypothesis_id},
        )
        return True
    
    async def remove_from_shadow(self, hypothesis_id: str) -> bool:
        """从 SHADOW 池移除"""
        if hypothesis_id in self._shadow_hypotheses:
            del self._shadow_hypotheses[hypothesis_id]
            logger.info(f"假设从 SHADOW 移除: {hypothesis_id}")
            return True
        return False
    
    async def is_in_shadow(self, hypothesis_id: str) -> bool:
        """检查假设是否在 SHADOW 运行中"""
        return hypothesis_id in self._shadow_hypotheses
