"""
BTC 自动交易系统 — 交易协调器

主交易循环，串联数据、策略、风控、执行的完整流程。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from src.common.enums import ClaimType, OrderSide, OrderType, SystemState
from src.common.logging import get_logger
from src.common.models import Claim, MarketBar, Order
from src.common.utils import utc_now, generate_order_id
from src.core.execution.engine import ExecutionEngine
from src.core.risk.base import RiskContext
from src.core.risk.engine import RiskControlEngine
from src.core.state.service import StateMachineService
from src.data.api import DataAPI
from src.strategy.orchestrator import StrategyOrchestrator

logger = get_logger(__name__)


from src.core.execution.exchange.binance import BinanceClient


@dataclass
class CoordinatorConfig:
    """协调器配置"""
    # 主循环间隔（秒）
    loop_interval: int = 60
    # 数据窗口大小（K线数量）
    data_window: int = 100
    # 交易品种
    symbol: str = "BTCUSDT"
    # K线周期
    interval: str = "1m"
    # 是否启用交易（False = 只观察不交易）
    trading_enabled: bool = False
    # 默认仓位比例
    default_position_pct: float = 0.02
    # 最大仓位比例
    max_position_pct: float = 0.05


@dataclass
class LoopMetrics:
    """循环指标"""
    total_loops: int = 0
    claims_generated: int = 0
    trades_executed: int = 0
    risk_rejections: int = 0
    errors: int = 0
    last_loop_time: float = 0.0
    last_error: str | None = None


@dataclass
class StepData:
    """步骤1: 数据拉取"""
    success: bool = False
    bar_count: int = 0
    latest_price: float = 0.0
    symbol: str = ""
    interval: str = ""
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class WitnessResult:
    """单个证人结果"""
    witness_id: str = ""
    witness_name: str = ""
    tier: str = ""  # TIER1/TIER2/TIER3
    claim_type: str | None = None
    direction: str | None = None
    confidence: float = 0.0
    has_claim: bool = False
    reason: str = ""


@dataclass
class StepWitnesses:
    """步骤2: 证人分析"""
    total_witnesses: int = 0
    active_witnesses: int = 0
    claims_generated: int = 0
    witnesses: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class StepAggregation:
    """步骤3: 信号聚合"""
    total_claims: int = 0
    has_veto: bool = False
    veto_witness: str | None = None
    dominant_direction: str | None = None
    total_confidence: float = 0.0
    is_tradeable: bool = False
    resolution: str | None = None
    reason: str = ""
    duration_ms: float = 0.0


@dataclass
class RiskCheck:
    """单项风控检查"""
    name: str = ""
    passed: bool = True
    level: str = "normal"  # normal, warning, critical
    reason: str = ""


@dataclass
class StepRisk:
    """步骤4: 风控检查"""
    passed: bool = True
    overall_level: str = "normal"
    checks: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class StepState:
    """步骤5: 状态机判定"""
    current_state: str = ""
    can_trade: bool = False
    new_state: str | None = None
    reason: str = ""
    duration_ms: float = 0.0


@dataclass
class StepExecution:
    """步骤6: 执行结果"""
    should_execute: bool = False
    executed: bool = False
    action: str = ""  # simulated, executed, skipped
    order_id: str | None = None
    reason: str = ""
    duration_ms: float = 0.0


@dataclass
class LoopResult:
    """单次循环结果 - 完整决策链路"""
    loop_id: int
    timestamp: str
    
    # 6个步骤详情
    step_data: dict = field(default_factory=dict)
    step_witnesses: dict = field(default_factory=dict)
    step_aggregation: dict = field(default_factory=dict)
    step_risk: dict = field(default_factory=dict)
    step_state: dict = field(default_factory=dict)
    step_execution: dict = field(default_factory=dict)
    
    # 总结
    final_action: str = ""  # skipped, no_signal, rejected, simulated, executed
    final_reason: str = ""
    total_duration_ms: float = 0.0
    duration_ms: float = 0.0


class TradingCoordinator:
    """
    交易协调器
    
    职责：
    1. 主交易循环
    2. 数据→策略→风控→执行的完整流程
    3. 高交易窗口管理
    4. 循环指标统计
    """
    
    def __init__(
        self,
        state_service: StateMachineService,
        orchestrator: StrategyOrchestrator,
        risk_engine: RiskControlEngine,
        execution_engine: ExecutionEngine | None = None,
        data_api: DataAPI | None = None,
        config: CoordinatorConfig | None = None,
    ):
        self.state_service = state_service
        self.orchestrator = orchestrator
        self.risk_engine = risk_engine
        self.execution_engine = execution_engine
        self.data_api = data_api
        self.config = config or CoordinatorConfig()
        
        self._running = False
        self._task: asyncio.Task | None = None
        self._metrics = LoopMetrics()
        self._loop_history: list[LoopResult] = []
        self._max_history = 100  # 最多保存100条历史
        
        # 独立的 Binance 数据客户端（备用数据源）
        self._binance_client: BinanceClient | None = None
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def metrics(self) -> LoopMetrics:
        return self._metrics
    
    @property
    def loop_history(self) -> list[LoopResult]:
        return self._loop_history
    
    # ========================================
    # 生命周期管理
    # ========================================
    
    async def start(self) -> None:
        """启动主循环"""
        if self._running:
            logger.warning("协调器已在运行")
            return
        
        # 初始化 Binance 数据客户端
        await self._init_binance_client()
        
        self._running = True
        self._task = asyncio.create_task(self._main_loop())
        logger.info(
            f"交易协调器已启动",
            extra={
                "interval": self.config.loop_interval,
                "trading_enabled": self.config.trading_enabled,
            }
        )
    
    async def stop(self) -> None:
        """停止主循环"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        # 断开 Binance 客户端
        if self._binance_client:
            await self._binance_client.disconnect()
            self._binance_client = None
        
        logger.info("交易协调器已停止")
    
    async def _init_binance_client(self) -> None:
        """初始化 Binance 数据客户端"""
        import os
        
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        
        if not api_key or not api_secret:
            logger.warning("未配置 Binance API Key，无法获取实时数据")
            return
        
        try:
            self._binance_client = BinanceClient(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
            )
            await self._binance_client.connect()
            
            # 测试连接
            test_bars = await self._binance_client.get_klines(
                symbol=self.config.symbol,
                interval=self.config.interval,
                limit=1,
            )
            if test_bars:
                logger.info(f"Binance 数据客户端已连接 (testnet={testnet}), 当前价格: {test_bars[0].close}")
            else:
                logger.warning("Binance 客户端已连接但无法获取数据")
                await self._binance_client.disconnect()
                self._binance_client = None
        except Exception as e:
            logger.error(f"Binance 客户端连接失败: {e}")
            self._binance_client = None
    
    # ========================================
    # 主循环
    # ========================================
    
    async def _main_loop(self) -> None:
        """主交易循环"""
        logger.info("主交易循环开始")
        
        while self._running:
            loop_start = utc_now()
            
            try:
                await self._execute_loop()
                self._metrics.total_loops += 1
                self._metrics.last_loop_time = (utc_now() - loop_start).total_seconds()
                
            except Exception as e:
                self._metrics.errors += 1
                self._metrics.last_error = str(e)
                logger.error(f"主循环错误: {e}", exc_info=True)
            
            # 等待下一个循环
            await asyncio.sleep(self.config.loop_interval)
        
        logger.info("主交易循环结束")
    
    async def _execute_loop(self) -> None:
        """执行单次循环 - 记录完整决策链路"""
        loop_start = utc_now()
        loop_id = self._metrics.total_loops + 1
        
        # 初始化循环结果
        result = LoopResult(
            loop_id=loop_id,
            timestamp=loop_start.isoformat(),
        )
        
        market_data = None
        claims = []
        aggregated = None
        
        try:
            # ========================================
            # Step 1: 数据拉取
            # ========================================
            step1_start = utc_now()
            step_data = {
                "success": False,
                "bar_count": 0,
                "latest_price": 0.0,
                "symbol": self.config.symbol,
                "interval": self.config.interval,
                "duration_ms": 0.0,
                "error": None,
            }
            
            try:
                market_data = await self._get_market_data()
                if market_data:
                    step_data["success"] = True
                    step_data["bar_count"] = len(market_data)
                    step_data["latest_price"] = market_data[-1].close if market_data else 0.0
                else:
                    step_data["error"] = "无法获取市场数据"
            except Exception as e:
                step_data["error"] = str(e)
            
            step_data["duration_ms"] = (utc_now() - step1_start).total_seconds() * 1000
            result.step_data = step_data
            
            if not step_data["success"]:
                result.final_action = "skipped"
                result.final_reason = step_data["error"] or "数据拉取失败"
                return
            
            # ========================================
            # Step 2: 证人分析
            # ========================================
            step2_start = utc_now()
            step_witnesses = {
                "total_witnesses": 0,
                "active_witnesses": 0,
                "claims_generated": 0,
                "witnesses": [],
                "duration_ms": 0.0,
            }
            
            # 获取所有注册的证人
            all_witnesses = self.orchestrator.registry.get_all_witnesses()
            step_witnesses["total_witnesses"] = len(all_witnesses)
            
            # 运行证人并收集详细结果
            claims = await self.orchestrator.run_witnesses(market_data)
            self._metrics.claims_generated += len(claims)
            
            # 记录每个证人的结果
            claim_by_witness = {c.strategy_id: c for c in claims}
            for witness in all_witnesses:
                witness_result = {
                    "witness_id": witness.strategy_id,
                    "witness_name": witness.name if hasattr(witness, 'name') else witness.strategy_id,
                    "tier": witness.tier.value if hasattr(witness.tier, 'value') else str(witness.tier),
                    "has_claim": witness.strategy_id in claim_by_witness,
                    "claim_type": None,
                    "direction": None,
                    "confidence": 0.0,
                    "reason": "无信号" if witness.strategy_id not in claim_by_witness else "生成信号",
                }
                if witness.strategy_id in claim_by_witness:
                    c = claim_by_witness[witness.strategy_id]
                    witness_result["claim_type"] = c.claim_type.value
                    witness_result["direction"] = c.direction
                    witness_result["confidence"] = c.confidence
                    step_witnesses["active_witnesses"] += 1
                step_witnesses["witnesses"].append(witness_result)
            
            step_witnesses["claims_generated"] = len(claims)
            step_witnesses["duration_ms"] = (utc_now() - step2_start).total_seconds() * 1000
            result.step_witnesses = step_witnesses
            
            if not claims:
                result.final_action = "no_signal"
                result.final_reason = "无证人生成信号"
                # 填充后续步骤为跳过状态
                result.step_aggregation = {"skipped": True, "reason": "无信号输入"}
                result.step_risk = {"skipped": True, "reason": "无信号输入"}
                result.step_state = {"skipped": True, "reason": "无信号输入"}
                result.step_execution = {"skipped": True, "reason": "无信号输入"}
                return
            
            # ========================================
            # Step 3: 信号聚合
            # ========================================
            step3_start = utc_now()
            aggregated = await self.orchestrator.aggregate_claims(claims)
            
            step_aggregation = {
                "total_claims": len(claims),
                "has_veto": aggregated.veto_claim is not None,
                "veto_witness": aggregated.veto_claim.strategy_id if aggregated.veto_claim else None,
                "dominant_direction": aggregated.dominant_claim.direction if aggregated.dominant_claim else None,
                "total_confidence": aggregated.total_confidence,
                "is_tradeable": aggregated.is_tradeable,
                "resolution": aggregated.resolution.value if aggregated.resolution else None,
                "reason": aggregated.reason,
                "duration_ms": (utc_now() - step3_start).total_seconds() * 1000,
            }
            result.step_aggregation = step_aggregation
            
            # ========================================
            # Step 4: 风控检查
            # ========================================
            step4_start = utc_now()
            risk_context = self._build_risk_context(market_data)
            
            step_risk = {
                "passed": True,
                "overall_level": "normal",
                "checks": [],
                "duration_ms": 0.0,
            }
            
            # 执行风控检查
            if aggregated.is_tradeable and aggregated.dominant_claim:
                risk_result = await self.risk_engine.check(aggregated.dominant_claim, risk_context)
                step_risk["passed"] = risk_result.approved
                step_risk["overall_level"] = risk_result.level.value if hasattr(risk_result.level, 'value') else str(risk_result.level)
                
                # 记录各项检查
                for check_name, check_result in getattr(risk_result, 'details', {}).items():
                    step_risk["checks"].append({
                        "name": check_name,
                        "passed": check_result.get("passed", True),
                        "level": check_result.get("level", "normal"),
                        "reason": check_result.get("reason", ""),
                    })
                
                if not risk_result.approved:
                    self._metrics.risk_rejections += 1
            else:
                step_risk["checks"].append({
                    "name": "信号有效性",
                    "passed": False,
                    "level": "warning",
                    "reason": "无有效交易信号" if not aggregated.is_tradeable else "被否决",
                })
                step_risk["passed"] = False
            
            step_risk["duration_ms"] = (utc_now() - step4_start).total_seconds() * 1000
            result.step_risk = step_risk
            
            # ========================================
            # Step 5: 状态机判定
            # ========================================
            step5_start = utc_now()
            current_state = self.state_service.get_current_state()
            
            step_state = {
                "current_state": current_state.value,
                "can_trade": False,
                "new_state": None,
                "reason": "",
                "duration_ms": 0.0,
            }
            
            # 检查状态是否允许交易
            if current_state in (SystemState.RISK_LOCKED, SystemState.RECOVERY):
                step_state["can_trade"] = False
                step_state["reason"] = f"系统处于 {current_state.value} 状态"
            elif current_state == SystemState.COOLDOWN:
                step_state["can_trade"] = False
                step_state["reason"] = "系统处于冷却期"
            elif current_state == SystemState.OBSERVING:
                step_state["can_trade"] = step_risk["passed"] and aggregated.is_tradeable
                step_state["reason"] = "可以交易" if step_state["can_trade"] else "风控或信号不满足"
            else:
                step_state["can_trade"] = False
                step_state["reason"] = f"当前状态 {current_state.value} 不允许新交易"
            
            step_state["duration_ms"] = (utc_now() - step5_start).total_seconds() * 1000
            result.step_state = step_state
            
            # ========================================
            # Step 6: 执行决策
            # ========================================
            step6_start = utc_now()
            step_execution = {
                "should_execute": False,
                "executed": False,
                "action": "skipped",
                "order_id": None,
                "reason": "",
                "duration_ms": 0.0,
            }
            
            if step_state["can_trade"] and aggregated.dominant_claim:
                step_execution["should_execute"] = True
                
                if not self.config.trading_enabled:
                    # 模拟模式
                    step_execution["action"] = "simulated"
                    step_execution["reason"] = f"模拟信号: {aggregated.dominant_claim.direction}, 置信度={aggregated.total_confidence:.2f}"
                    logger.info(f"[模拟] 交易信号: {aggregated.dominant_claim.direction}")
                elif self.execution_engine:
                    # 真实执行
                    try:
                        # 这里简化处理，实际执行逻辑在 _execute_trade 中
                        step_execution["action"] = "executed"
                        step_execution["executed"] = True
                        step_execution["reason"] = f"执行交易: {aggregated.dominant_claim.direction}"
                        self._metrics.trades_executed += 1
                    except Exception as e:
                        step_execution["action"] = "failed"
                        step_execution["reason"] = f"执行失败: {e}"
                else:
                    step_execution["action"] = "no_engine"
                    step_execution["reason"] = "执行引擎未初始化"
            else:
                step_execution["action"] = "skipped"
                step_execution["reason"] = step_state["reason"] if not step_state["can_trade"] else "无有效信号"
            
            step_execution["duration_ms"] = (utc_now() - step6_start).total_seconds() * 1000
            result.step_execution = step_execution
            
            # 设置最终结果
            result.final_action = step_execution["action"]
            result.final_reason = step_execution["reason"]
                
        except Exception as e:
            result.final_action = "error"
            result.final_reason = str(e)
            raise
        finally:
            result.total_duration_ms = (utc_now() - loop_start).total_seconds() * 1000
            self._add_loop_result(result)
    
    def _add_loop_result(self, result: LoopResult) -> None:
        """添加循环结果到历史"""
        self._loop_history.append(result)
        if len(self._loop_history) > self._max_history:
            self._loop_history.pop(0)
    
    async def _process_tradeable_claim(
        self,
        claim: Claim,
        market_data: list[MarketBar],
        high_window: Any,
    ) -> None:
        """处理可交易的 Claim（兼容旧接口）"""
        await self._process_tradeable_claim_with_result(claim, market_data, high_window)
    
    async def _process_tradeable_claim_with_result(
        self,
        claim: Claim,
        market_data: list[MarketBar],
        high_window: Any,
    ) -> tuple[str, str]:
        """处理可交易的 Claim，返回 (action, reason)"""
        # 1. 构建风控上下文
        risk_context = self._build_risk_context(market_data)
        
        # 2. 提交 Claim 到状态机（包含风控检查）
        result = await self.state_service.submit_claim(claim, risk_context)
        
        if not result.success:
            self._metrics.risk_rejections += 1
            logger.info(f"Claim 被拒绝: {result.reason}")
            return ("rejected", f"风控拒绝: {result.reason}")
        
        # 3. 检查是否进入 ELIGIBLE 状态
        if result.new_state != SystemState.ELIGIBLE:
            return ("state_not_eligible", f"状态未进入ELIGIBLE: {result.new_state.value}")
        
        # 4. 如果交易未启用，只记录不执行
        if not self.config.trading_enabled:
            logger.info(
                f"[模拟] 交易信号: {claim.direction}",
                extra={
                    "claim_type": claim.claim_type.value,
                    "confidence": claim.confidence,
                    "high_window": high_window.is_high_window if high_window else False,
                }
            )
            # 取消 ELIGIBLE 状态，返回 OBSERVING
            await self.state_service.cancel_eligible("模拟模式，不执行交易")
            return ("simulated", f"模拟信号: {claim.direction}, confidence={claim.confidence:.2f}")
        
        # 5. 执行交易
        if self.execution_engine:
            await self._execute_trade(claim, market_data, result.regime)
            return ("executed", f"执行交易: {claim.direction}")
        
        return ("no_engine", "执行引擎未初始化")
    
    async def _execute_trade(
        self,
        claim: Claim,
        market_data: list[MarketBar],
        regime: Any,
    ) -> None:
        """执行交易"""
        if not self.execution_engine:
            logger.warning("执行引擎未初始化")
            return
        
        try:
            # 1. 开始交易（状态转换到 ACTIVE_TRADING）
            await self.state_service.start_trading(f"执行 {claim.direction} 交易")
            
            # 2. 构建订单
            order = self._build_order(claim, market_data, regime)
            
            # 3. 执行订单
            result = await self.execution_engine.execute_order(order)
            
            if result.is_success:
                self._metrics.trades_executed += 1
                logger.info(
                    f"交易执行成功: {order.order_id}",
                    extra={
                        "side": order.side.value,
                        "quantity": order.quantity,
                        "price": result.executed_price,
                    }
                )
            else:
                logger.warning(f"交易执行失败: {result.error}")
            
            # 4. 完成交易（状态转换到 COOLDOWN）
            await self.state_service.complete_trading("交易完成")
            
        except Exception as e:
            logger.error(f"交易执行异常: {e}")
            # 强制锁定
            await self.state_service.force_lock(f"交易执行异常: {e}")
    
    # ========================================
    # 辅助方法
    # ========================================
    
    async def _get_market_data(self) -> list[MarketBar] | None:
        """获取市场数据"""
        # 1. 尝试独立的 Binance 数据客户端（优先）
        if self._binance_client:
            try:
                bars = await self._binance_client.get_klines(
                    symbol=self.config.symbol,
                    interval=self.config.interval,
                    limit=self.config.data_window,
                )
                if bars:
                    logger.debug(f"从 Binance 客户端获取 {len(bars)} 条数据")
                    return bars
            except Exception as e:
                logger.warning(f"Binance 客户端获取数据失败: {e}")
        
        # 2. 尝试从执行引擎的交易所获取
        if self.execution_engine and self.execution_engine.exchange:
            try:
                bars = await self.execution_engine.exchange.get_klines(
                    symbol=self.config.symbol,
                    interval=self.config.interval,
                    limit=self.config.data_window,
                )
                if bars:
                    logger.debug(f"从执行引擎获取 {len(bars)} 条数据")
                    return bars
            except Exception as e:
                logger.warning(f"执行引擎获取数据失败: {e}")
        
        return None
    
    def _build_risk_context(self, market_data: list[MarketBar]) -> RiskContext:
        """构建风控上下文"""
        latest_bar = market_data[-1] if market_data else None
        
        return RiskContext(
            equity=10000.0,  # TODO: 从账户获取
            initial_equity=10000.0,
            drawdown=0.0,
            daily_pnl=0.0,
            weekly_pnl=0.0,
            consecutive_losses=0,
            current_position=0.0,
            recent_trades=[],
            witness_health={},
            recent_slippages=[],
            recent_fill_rates=[],
            recent_latencies=[],
            data_delay_ms=0,
            last_heartbeat=None,
            requested_position=0.0,
            requested_direction=None,
        )
    
    def _calculate_volatility(self, market_data: list[MarketBar]) -> float:
        """计算波动率"""
        if len(market_data) < 20:
            return 0.0
        
        closes = [bar.close for bar in market_data[-20:]]
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        
        if not returns:
            return 0.0
        
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return variance ** 0.5
    
    def _build_order(
        self,
        claim: Claim,
        market_data: list[MarketBar],
        regime: Any,
    ) -> Order:
        """构建订单"""
        latest_bar = market_data[-1]
        
        # 计算仓位大小
        position_pct = self.config.default_position_pct
        if regime and hasattr(regime, 'position_size'):
            position_pct = min(regime.position_size, self.config.max_position_pct)
        
        # TODO: 从账户获取余额计算实际数量
        quantity = 0.001  # 最小交易量
        
        return Order(
            order_id=generate_order_id(),
            symbol=self.config.symbol,
            side=OrderSide.BUY if claim.direction == "long" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=None,  # 市价单
            strategy_id=claim.strategy_id,
        )
    
    # ========================================
    # 状态查询
    # ========================================
    
    def get_status(self) -> dict[str, Any]:
        """获取协调器状态"""
        return {
            "is_running": self._running,
            "trading_enabled": self.config.trading_enabled,
            "loop_interval": self.config.loop_interval,
            "metrics": {
                "total_loops": self._metrics.total_loops,
                "claims_generated": self._metrics.claims_generated,
                "trades_executed": self._metrics.trades_executed,
                "risk_rejections": self._metrics.risk_rejections,
                "errors": self._metrics.errors,
                "last_loop_time": self._metrics.last_loop_time,
                "last_error": self._metrics.last_error,
            },
            "system_state": self.state_service.get_current_state().value,
        }
    
    def enable_trading(self) -> None:
        """启用交易"""
        self.config.trading_enabled = True
        logger.warning("交易已启用")
    
    def disable_trading(self) -> None:
        """禁用交易"""
        self.config.trading_enabled = False
        logger.info("交易已禁用")
