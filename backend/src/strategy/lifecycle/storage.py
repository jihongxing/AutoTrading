"""
BTC 自动交易系统 — 生命周期状态存储

持久化策略状态变更历史和影子运行数据。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.logging import get_logger
from src.common.utils import utc_now

from .models import ShadowPerformance, ShadowTradeRecord, StrategyStateRecord

logger = get_logger(__name__)


class LifecycleStorage:
    """
    生命周期状态存储
    
    提供状态历史和影子运行数据的持久化。
    当前实现：文件存储（JSON）
    生产环境：应替换为 QuestDB
    """
    
    def __init__(self, data_dir: str = "data/lifecycle"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._state_file = self.data_dir / "state_history.json"
        self._shadow_times_file = self.data_dir / "shadow_times.json"
        self._shadow_records_dir = self.data_dir / "shadow_records"
        self._shadow_records_dir.mkdir(exist_ok=True)
    
    # === 状态历史 ===
    
    def save_state_history(self, records: list[StrategyStateRecord]) -> None:
        """保存状态变更历史"""
        data = [self._record_to_dict(r) for r in records]
        self._write_json(self._state_file, data)
        logger.debug(f"保存状态历史: {len(records)} 条")
    
    def load_state_history(self) -> list[StrategyStateRecord]:
        """加载状态变更历史"""
        data = self._read_json(self._state_file)
        if not data:
            return []
        
        records = []
        for item in data:
            try:
                records.append(self._dict_to_record(item))
            except Exception as e:
                logger.warning(f"解析状态记录失败: {e}")
        
        logger.debug(f"加载状态历史: {len(records)} 条")
        return records
    
    def append_state_record(self, record: StrategyStateRecord) -> None:
        """追加单条状态记录"""
        records = self.load_state_history()
        records.append(record)
        self.save_state_history(records)
    
    # === 影子运行时间 ===
    
    def save_shadow_times(self, times: dict[str, float]) -> None:
        """保存影子运行开始时间"""
        self._write_json(self._shadow_times_file, times)
    
    def load_shadow_times(self) -> dict[str, float]:
        """加载影子运行开始时间"""
        data = self._read_json(self._shadow_times_file)
        return data if data else {}
    
    # === 影子交易记录 ===
    
    def save_shadow_records(self, strategy_id: str, records: list[ShadowTradeRecord]) -> None:
        """保存影子交易记录"""
        file_path = self._shadow_records_dir / f"{strategy_id}.json"
        data = [self._shadow_record_to_dict(r) for r in records]
        self._write_json(file_path, data)
    
    def load_shadow_records(self, strategy_id: str) -> list[ShadowTradeRecord]:
        """加载影子交易记录"""
        file_path = self._shadow_records_dir / f"{strategy_id}.json"
        data = self._read_json(file_path)
        if not data:
            return []
        
        # 简化：返回空列表，实际需要反序列化 Claim
        # 生产环境应使用数据库存储
        return []
    
    def delete_shadow_records(self, strategy_id: str) -> None:
        """删除影子交易记录"""
        file_path = self._shadow_records_dir / f"{strategy_id}.json"
        if file_path.exists():
            file_path.unlink()
    
    # === 辅助方法 ===
    
    def _write_json(self, path: Path, data: Any) -> None:
        """写入 JSON 文件"""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"写入文件失败: {path}, {e}")
    
    def _read_json(self, path: Path) -> Any:
        """读取 JSON 文件"""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取文件失败: {path}, {e}")
            return None
    
    def _record_to_dict(self, record: StrategyStateRecord) -> dict:
        """状态记录转字典"""
        return {
            "strategy_id": record.strategy_id,
            "status": record.status,
            "previous_status": record.previous_status,
            "tier": record.tier.value if record.tier else None,
            "changed_at": record.changed_at.isoformat(),
            "reason": record.reason,
            "changed_by": record.changed_by,
        }
    
    def _dict_to_record(self, data: dict) -> StrategyStateRecord:
        """字典转状态记录"""
        from src.common.enums import WitnessTier
        
        tier = None
        if data.get("tier"):
            tier = WitnessTier(data["tier"])
        
        return StrategyStateRecord(
            strategy_id=data["strategy_id"],
            status=data["status"],
            previous_status=data.get("previous_status"),
            tier=tier,
            changed_at=datetime.fromisoformat(data["changed_at"]),
            reason=data["reason"],
            changed_by=data["changed_by"],
        )
    
    def _shadow_record_to_dict(self, record: ShadowTradeRecord) -> dict:
        """影子交易记录转字典"""
        return {
            "strategy_id": record.strategy_id,
            "timestamp": record.timestamp.isoformat(),
            "market_price": record.market_price,
            "simulated_entry": record.simulated_entry,
            "simulated_exit": record.simulated_exit,
            "simulated_pnl": record.simulated_pnl,
            "claim_type": record.claim.claim_type.value,
            "direction": record.claim.direction,
            "confidence": record.claim.confidence,
        }
