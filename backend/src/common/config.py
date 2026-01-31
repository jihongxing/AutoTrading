"""
BTC 自动交易系统 — 配置加载

支持 YAML 配置文件和环境变量替换。
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from .logging import get_logger

logger = get_logger(__name__)


class TradingConfig(BaseModel):
    """交易配置（L1）"""
    
    default_position_ratio: float = Field(default=0.02, ge=0.01, le=0.05)
    max_single_position: float = Field(default=0.05, ge=0.01, le=0.10)
    max_total_position: float = Field(default=0.30, ge=0.10, le=0.50)


class RiskConfig(BaseModel):
    """风控配置（L2）"""
    
    max_drawdown: float = Field(default=0.20, ge=0.05, le=0.30)
    daily_max_loss: float = Field(default=0.03, ge=0.01, le=0.10)
    weekly_max_loss: float = Field(default=0.10, ge=0.03, le=0.20)
    consecutive_loss_cooldown: int = Field(default=3, ge=2, le=5)


class WitnessConfig(BaseModel):
    """证人配置"""
    
    min_witnesses: int = Field(default=2, ge=2, le=5)
    core_aux_ratio: float = Field(default=2.0, ge=1.5, le=3.0)


class Settings(BaseModel):
    """系统配置"""
    
    env: str = Field(default="development")
    debug: bool = Field(default=False)
    
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    witness: WitnessConfig = Field(default_factory=WitnessConfig)
    
    # 数据库
    questdb_host: str = Field(default="localhost")
    questdb_port: int = Field(default=9000)
    
    # Kafka
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    
    # 交易所
    exchange_api_key: str = Field(default="")
    exchange_api_secret: str = Field(default="")


def _substitute_env_vars(value: Any) -> Any:
    """替换环境变量占位符 ${VAR_NAME}"""
    if isinstance(value, str):
        pattern = r"\$\{([^}]+)\}"
        
        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        return re.sub(pattern, replacer, value)
    
    if isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    
    if isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    
    return value


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """
    加载 YAML 配置文件
    
    Args:
        path: 配置文件路径
    
    Returns:
        配置字典
    """
    path = Path(path)
    
    if not path.exists():
        logger.warning(f"配置文件不存在: {path}")
        return {}
    
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    return _substitute_env_vars(data)


def load_settings(config_dir: str | Path | None = None) -> Settings:
    """
    加载系统配置
    
    优先级：环境变量 > config/*.yaml > 默认值
    
    Args:
        config_dir: 配置目录路径
    
    Returns:
        Settings 实例
    """
    config_data: dict[str, Any] = {}
    
    if config_dir:
        config_dir = Path(config_dir)
        
        # 加载主配置
        main_config = config_dir / "config.yaml"
        if main_config.exists():
            config_data.update(load_yaml_config(main_config))
        
        # 加载风控配置
        risk_config = config_dir / "risk.yaml"
        if risk_config.exists():
            risk_data = load_yaml_config(risk_config)
            if "risk" in risk_data:
                config_data.setdefault("risk", {}).update(risk_data["risk"])
            else:
                config_data.setdefault("risk", {}).update(risk_data)
    
    return Settings(**config_data)


# 全局配置实例（延迟初始化）
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取全局配置实例"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
