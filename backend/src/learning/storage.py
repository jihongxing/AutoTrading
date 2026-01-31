"""
BTC 自动交易系统 — 学习参数存储

参数持久化、版本管理和回滚支持。
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

logger = get_logger(__name__)


@dataclass
class LearningParams:
    """学习参数"""
    version: int
    timestamp: datetime
    
    # 仓位参数
    position_multiplier: float = 1.0
    default_position_ratio: float = 0.02
    
    # 止损止盈参数
    stop_loss: float = 0.02
    take_profit: float = 0.03
    
    # 窗口参数
    window_threshold: float = 0.6
    window_multiplier: float = 1.5
    
    # 证人权重
    witness_weights: dict[str, float] = field(default_factory=dict)
    
    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningParams":
        """从字典创建"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class LearningParamStorage:
    """
    学习参数存储
    
    功能：
    - 参数持久化
    - 版本管理
    - 回滚支持
    """
    
    def __init__(
        self,
        storage_path: str = "data/learning_params.json",
        max_history: int = 100,
    ):
        self.storage_path = Path(storage_path)
        self.max_history = max_history
        self._history: list[LearningParams] = []
        self._current: LearningParams | None = None
    
    async def save_params(self, params: LearningParams) -> None:
        """
        保存参数
        
        Args:
            params: 学习参数
        """
        # 添加到历史
        self._history.append(params)
        self._current = params
        
        # 限制历史数量
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]
        
        # 持久化
        await self._persist()
        
        logger.info(
            f"保存学习参数: version={params.version}",
            extra={"version": params.version},
        )
    
    async def load_params(self) -> LearningParams | None:
        """
        加载参数
        
        Returns:
            最新的学习参数
        """
        await self._load_from_file()
        return self._current
    
    async def rollback(self, version: int) -> LearningParams | None:
        """
        回滚到指定版本
        
        Args:
            version: 目标版本号
        
        Returns:
            回滚后的参数
        """
        for params in reversed(self._history):
            if params.version == version:
                self._current = params
                
                logger.info(
                    f"回滚到版本: {version}",
                    extra={"version": version},
                )
                
                return params
        
        logger.warning(f"版本不存在: {version}")
        return None
    
    async def get_history(self, limit: int = 10) -> list[LearningParams]:
        """
        获取历史版本
        
        Args:
            limit: 返回数量限制
        
        Returns:
            历史参数列表
        """
        return self._history[-limit:]
    
    async def get_version(self, version: int) -> LearningParams | None:
        """
        获取指定版本
        
        Args:
            version: 版本号
        
        Returns:
            学习参数
        """
        for params in self._history:
            if params.version == version:
                return params
        return None
    
    def create_new_version(self, base: LearningParams | None = None) -> LearningParams:
        """
        创建新版本
        
        Args:
            base: 基础参数（可选）
        
        Returns:
            新版本参数
        """
        new_version = (self._current.version + 1) if self._current else 1
        
        if base:
            return LearningParams(
                version=new_version,
                timestamp=utc_now(),
                position_multiplier=base.position_multiplier,
                default_position_ratio=base.default_position_ratio,
                stop_loss=base.stop_loss,
                take_profit=base.take_profit,
                window_threshold=base.window_threshold,
                window_multiplier=base.window_multiplier,
                witness_weights=base.witness_weights.copy(),
            )
        else:
            return LearningParams(
                version=new_version,
                timestamp=utc_now(),
            )
    
    async def _persist(self) -> None:
        """持久化到文件"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "current_version": self._current.version if self._current else 0,
                "history": [p.to_dict() for p in self._history],
            }
            
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"持久化失败: {e}", extra={"error": str(e)})
    
    async def _load_from_file(self) -> None:
        """从文件加载"""
        if not self.storage_path.exists():
            logger.info("参数文件不存在，使用默认值")
            return
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._history = [
                LearningParams.from_dict(p) for p in data.get("history", [])
            ]
            
            current_version = data.get("current_version", 0)
            for params in self._history:
                if params.version == current_version:
                    self._current = params
                    break
            
            logger.info(
                f"加载学习参数: {len(self._history)} 个版本",
                extra={"versions": len(self._history)},
            )
            
        except Exception as e:
            logger.error(f"加载失败: {e}", extra={"error": str(e)})
