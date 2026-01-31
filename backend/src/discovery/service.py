"""
BTC 自动交易系统 — 发现服务

整合假设工厂、候选池、验证器，提供完整的自发现流程。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.common.enums import HypothesisStatus
from src.common.logging import get_logger
from src.common.models import MarketBar
from src.common.utils import utc_now

from .factory.engine import HypothesisFactory
from .factory.detectors import (
    VolatilityDetector,
    VolumeDetector,
    PricePatternDetector,
)
from .pool.manager import HypothesisPoolManager
from .pool.models import AnomalyEvent, Hypothesis
from .validator.engine import HypothesisValidator

logger = get_logger(__name__)


@dataclass
class ScanResult:
    """扫描结果"""
    timestamp: datetime
    events_found: int
    hypotheses_generated: int
    hypotheses_added: int
    events: list[dict] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class DiscoveryStats:
    """发现统计"""
    total_scans: int = 0
    total_events: int = 0
    total_hypotheses: int = 0
    last_scan_time: datetime | None = None
    pool_stats: dict[str, int] = field(default_factory=dict)


class DiscoveryService:
    """
    发现服务
    
    职责：
    1. 初始化并管理检测器
    2. 定时扫描市场数据
    3. 管理假设候选池
    4. 触发验证流程
    """
    
    def __init__(
        self,
        scan_interval: int = 3600,  # 扫描间隔（秒），默认1小时
    ):
        self.scan_interval = scan_interval
        
        # 核心组件
        self.factory = HypothesisFactory()
        self.pool = HypothesisPoolManager()
        self.validator = HypothesisValidator()
        
        # 状态
        self._running = False
        self._task: asyncio.Task | None = None
        self._stats = DiscoveryStats()
        self._scan_history: list[ScanResult] = []
        self._max_history = 50
        
        # 数据获取回调
        self._data_fetcher: Any = None
        
        # 初始化检测器
        self._init_detectors()
    
    def _init_detectors(self) -> None:
        """初始化默认检测器"""
        self.factory.register_detector(VolatilityDetector())
        self.factory.register_detector(VolumeDetector())
        self.factory.register_detector(PricePatternDetector())
        
        logger.info(f"已注册 {self.factory.detector_count} 个检测器")
    
    def set_data_fetcher(self, fetcher: Any) -> None:
        """设置数据获取器"""
        self._data_fetcher = fetcher
    
    async def start(self) -> None:
        """启动发现服务"""
        if self._running:
            logger.warning("发现服务已在运行")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info(f"发现服务已启动，扫描间隔: {self.scan_interval}s")
    
    async def stop(self) -> None:
        """停止发现服务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("发现服务已停止")
    
    async def _scan_loop(self) -> None:
        """扫描循环"""
        while self._running:
            try:
                await self.run_scan()
            except Exception as e:
                logger.error(f"扫描异常: {e}", exc_info=True)
            
            await asyncio.sleep(self.scan_interval)
    
    async def run_scan(self, data: list[MarketBar] | None = None) -> ScanResult:
        """
        运行一次扫描
        
        Args:
            data: K线数据，如果为空则尝试从 data_fetcher 获取
        
        Returns:
            扫描结果
        """
        start_time = utc_now()
        result = ScanResult(timestamp=start_time, events_found=0, hypotheses_generated=0, hypotheses_added=0)
        
        # 获取数据
        if data is None:
            data = await self._fetch_data()
        
        if not data or len(data) < 50:
            logger.warning("数据不足，跳过扫描")
            return result
        
        # 扫描异常
        events = await self.factory.scan_for_anomalies(data)
        result.events_found = len(events)
        result.events = [self._event_to_dict(e) for e in events]
        
        # 生成假设
        hypotheses = self.factory.generate_hypotheses(events)
        result.hypotheses_generated = len(hypotheses)
        
        # 添加到候选池
        added = 0
        for h in hypotheses:
            if await self.pool.add(h):
                added += 1
                result.hypotheses.append(self._hypothesis_to_dict(h))
        result.hypotheses_added = added
        
        # 更新统计
        self._stats.total_scans += 1
        self._stats.total_events += len(events)
        self._stats.total_hypotheses += added
        self._stats.last_scan_time = start_time
        self._stats.pool_stats = self.pool.get_statistics()
        
        result.duration_ms = (utc_now() - start_time).total_seconds() * 1000
        
        # 保存历史
        self._scan_history.append(result)
        if len(self._scan_history) > self._max_history:
            self._scan_history.pop(0)
        
        logger.info(
            f"扫描完成: 事件={len(events)}, 假设={len(hypotheses)}, 入池={added}",
            extra={"events": len(events), "hypotheses": len(hypotheses), "added": added},
        )
        
        return result
    
    async def _fetch_data(self) -> list[MarketBar] | None:
        """获取市场数据"""
        if self._data_fetcher is None:
            logger.warning("未配置数据获取器")
            return None
        
        try:
            return await self._data_fetcher.get_klines(
                symbol="BTCUSDT",
                interval="1h",
                limit=200,
            )
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return None
    
    async def validate_hypothesis(self, hypothesis_id: str) -> dict[str, Any]:
        """
        验证假设
        
        Args:
            hypothesis_id: 假设 ID
        
        Returns:
            验证结果
        """
        hypothesis = await self.pool.get(hypothesis_id)
        if not hypothesis:
            return {"success": False, "error": "假设不存在"}
        
        # 更新状态为验证中
        await self.pool.update_status(hypothesis_id, HypothesisStatus.VALIDATING)
        
        try:
            # 模拟验证结果（实际应该运行回测）
            # TODO: 接入真实回测引擎
            import random
            from src.discovery.pool.models import ValidationResult
            
            # 生成模拟验证结果
            win_rate = random.uniform(0.45, 0.58)
            sharpe = random.uniform(0.3, 1.5)
            is_robust = win_rate >= 0.50 and random.random() > 0.3
            
            result = ValidationResult(
                p_value=random.uniform(0.01, 0.3),
                win_rate=win_rate,
                cohens_d=random.uniform(0.1, 0.5),
                sample_size=random.randint(100, 500),
                is_robust=is_robust,
                correlation_max=random.uniform(0, 0.3),
                sharpe_ratio=sharpe,
                profit_factor=random.uniform(0.8, 1.5),
            )
            
            # 根据结果更新状态
            if result.is_robust and result.win_rate >= 0.52:
                if result.sharpe_ratio >= 1.0:
                    new_status = HypothesisStatus.TIER_1
                else:
                    new_status = HypothesisStatus.TIER_2
            elif result.win_rate >= 0.48:
                new_status = HypothesisStatus.TIER_3
            else:
                new_status = HypothesisStatus.FAIL
            
            await self.pool.update_status(hypothesis_id, new_status)
            hypothesis.set_validation_result(result)
            
            return {
                "success": True,
                "hypothesis_id": hypothesis_id,
                "new_status": new_status.value,
                "validation": {
                    "win_rate": result.win_rate,
                    "sharpe_ratio": result.sharpe_ratio,
                    "is_robust": result.is_robust,
                    "sample_size": result.sample_size,
                    "p_value": result.p_value,
                },
            }
        except Exception as e:
            logger.error(f"验证失败: {e}")
            await self.pool.update_status(hypothesis_id, HypothesisStatus.FAIL)
            return {"success": False, "error": str(e)}
    
    async def promote_hypothesis(self, hypothesis_id: str) -> dict[str, Any]:
        """
        晋升假设到 SHADOW 运行
        
        Args:
            hypothesis_id: 假设 ID
        
        Returns:
            晋升结果
        """
        success = await self.pool.promote_to_shadow(hypothesis_id)
        if success:
            return {"success": True, "hypothesis_id": hypothesis_id, "status": "shadow"}
        return {"success": False, "error": "晋升失败，假设不存在或状态不符合"}
    
    def get_status(self) -> dict[str, Any]:
        """获取服务状态"""
        return {
            "is_running": self._running,
            "scan_interval": self.scan_interval,
            "detector_count": self.factory.detector_count,
            "detectors": self.factory.detector_ids,
            "stats": {
                "total_scans": self._stats.total_scans,
                "total_events": self._stats.total_events,
                "total_hypotheses": self._stats.total_hypotheses,
                "last_scan_time": self._stats.last_scan_time.isoformat() if self._stats.last_scan_time else None,
            },
            "pool_stats": self.pool.get_statistics(),
        }
    
    def get_scan_history(self, limit: int = 20) -> list[dict]:
        """获取扫描历史"""
        recent = list(reversed(self._scan_history[-limit:]))
        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "events_found": r.events_found,
                "hypotheses_generated": r.hypotheses_generated,
                "hypotheses_added": r.hypotheses_added,
                "duration_ms": r.duration_ms,
            }
            for r in recent
        ]
    
    async def get_hypotheses(self, status: str | None = None) -> list[dict]:
        """获取假设列表"""
        if status:
            try:
                status_enum = HypothesisStatus(status)
                hypotheses = await self.pool.get_by_status(status_enum)
            except ValueError:
                hypotheses = await self.pool.get_all()
        else:
            hypotheses = await self.pool.get_all()
        
        return [self._hypothesis_to_dict(h) for h in hypotheses]
    
    async def get_hypothesis(self, hypothesis_id: str) -> dict | None:
        """获取假设详情"""
        h = await self.pool.get(hypothesis_id)
        if h:
            return self._hypothesis_to_dict(h)
        return None
    
    def _event_to_dict(self, event: AnomalyEvent) -> dict:
        """转换事件为字典"""
        return {
            "event_id": event.event_id,
            "detector_id": event.detector_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "severity": event.severity,
            "features": event.features,
        }
    
    def _hypothesis_to_dict(self, h: Hypothesis) -> dict:
        """转换假设为字典"""
        return {
            "id": h.id,
            "name": h.name,
            "status": h.status.value,
            "source_detector": h.source_detector,
            "source_event": h.source_event,
            "event_definition": h.event_definition,
            "event_params": h.event_params,
            "expected_direction": h.expected_direction,
            "expected_win_rate": list(h.expected_win_rate),
            "validation_result": {
                "win_rate": h.validation_result.win_rate,
                "sharpe_ratio": h.validation_result.sharpe_ratio,
                "is_robust": h.validation_result.is_robust,
                "sample_size": h.validation_result.sample_size,
            } if h.validation_result else None,
            "created_at": h.created_at.isoformat(),
            "updated_at": h.updated_at.isoformat(),
        }


# 全局实例
_discovery_service: DiscoveryService | None = None


def get_discovery_service() -> DiscoveryService | None:
    """获取发现服务实例"""
    return _discovery_service


def init_discovery_service(scan_interval: int = 3600) -> DiscoveryService:
    """初始化发现服务"""
    global _discovery_service
    _discovery_service = DiscoveryService(scan_interval=scan_interval)
    return _discovery_service
