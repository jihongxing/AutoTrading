"""
BTC 自动交易系统 — 假设工厂引擎

协调检测器扫描异常、生成假设。
"""

from datetime import datetime

from src.common.logging import get_logger
from src.common.models import MarketBar
from src.data.api import DataAPI, DataAccessRole
from src.data.storage import QuestDBStorage

from ..pool.models import AnomalyEvent, Hypothesis
from .detectors.base import BaseDetector

logger = get_logger(__name__)


class HypothesisFactory:
    """
    假设工厂
    
    协调多个检测器，扫描市场数据，生成策略假设。
    """
    
    def __init__(self, storage: QuestDBStorage | None = None):
        self._detectors: list[BaseDetector] = []
        self._storage = storage
        self._data_api: DataAPI | None = None
        if storage:
            self._data_api = DataAPI(storage, DataAccessRole.LEARNING)

    def register_detector(self, detector: BaseDetector) -> None:
        """注册检测器"""
        self._detectors.append(detector)
        logger.info(f"检测器已注册: {detector.detector_id}")
    
    def unregister_detector(self, detector_id: str) -> bool:
        """注销检测器"""
        for i, d in enumerate(self._detectors):
            if d.detector_id == detector_id:
                self._detectors.pop(i)
                logger.info(f"检测器已注销: {detector_id}")
                return True
        return False
    
    async def scan_for_anomalies(
        self,
        data: list[MarketBar],
    ) -> list[AnomalyEvent]:
        """
        扫描异常事件
        
        Args:
            data: K 线数据
        
        Returns:
            所有检测器发现的异常事件
        """
        all_events: list[AnomalyEvent] = []
        
        for detector in self._detectors:
            try:
                events = await detector.detect(data)
                all_events.extend(events)
                if events:
                    logger.info(
                        f"检测器 {detector.detector_id} 发现 {len(events)} 个异常",
                        extra={"detector": detector.detector_id, "count": len(events)},
                    )
            except Exception as e:
                logger.error(f"检测器 {detector.detector_id} 异常: {e}")
        
        return all_events

    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """
        从异常事件生成假设
        
        Args:
            events: 异常事件列表
        
        Returns:
            假设列表
        """
        all_hypotheses: list[Hypothesis] = []
        
        # 按检测器分组
        events_by_detector: dict[str, list[AnomalyEvent]] = {}
        for event in events:
            if event.detector_id not in events_by_detector:
                events_by_detector[event.detector_id] = []
            events_by_detector[event.detector_id].append(event)
        
        # 各检测器生成假设
        for detector in self._detectors:
            detector_events = events_by_detector.get(detector.detector_id, [])
            if detector_events:
                hypotheses = detector.generate_hypotheses(detector_events)
                all_hypotheses.extend(hypotheses)
        
        logger.info(f"生成 {len(all_hypotheses)} 个假设")
        return all_hypotheses
    
    async def run_scan(
        self,
        start: datetime,
        end: datetime,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
    ) -> tuple[list[AnomalyEvent], list[Hypothesis]]:
        """
        运行完整扫描流程
        
        Args:
            start: 开始时间
            end: 结束时间
            symbol: 交易对
            interval: K 线周期
        
        Returns:
            (异常事件列表, 假设列表)
        """
        if not self._data_api:
            raise RuntimeError("未配置数据存储")
        
        # 获取数据
        data = await self._data_api.get_bars(symbol, interval, start, end)
        if not data:
            logger.warning("无数据可扫描")
            return [], []
        
        # 扫描异常
        events = await self.scan_for_anomalies(data)
        
        # 生成假设
        hypotheses = self.generate_hypotheses(events)
        
        return events, hypotheses
    
    @property
    def detector_count(self) -> int:
        """检测器数量"""
        return len(self._detectors)
    
    @property
    def detector_ids(self) -> list[str]:
        """检测器 ID 列表"""
        return [d.detector_id for d in self._detectors]
