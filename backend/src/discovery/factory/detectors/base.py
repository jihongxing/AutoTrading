"""
BTC 自动交易系统 — 异常检测器基类

所有检测器必须继承此基类。
"""

from abc import ABC, abstractmethod

from src.common.models import MarketBar

from ...pool.models import AnomalyEvent, Hypothesis


class BaseDetector(ABC):
    """
    异常检测器基类
    
    检测器职责：
    1. 检测市场异常事件
    2. 从异常事件生成策略假设
    """
    
    detector_id: str
    detector_name: str
    
    @abstractmethod
    async def detect(self, data: list[MarketBar]) -> list[AnomalyEvent]:
        """
        检测异常事件
        
        Args:
            data: K 线数据
        
        Returns:
            异常事件列表
        """
        pass
    
    @abstractmethod
    def generate_hypotheses(self, events: list[AnomalyEvent]) -> list[Hypothesis]:
        """
        从异常事件生成假设
        
        Args:
            events: 异常事件列表
        
        Returns:
            假设列表
        """
        pass
