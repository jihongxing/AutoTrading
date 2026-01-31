# Discovery 假设工厂 — 任务清单

## 阶段 1: 基础设施 (P0)

- [x] Task 1: 扩展 `src/common/enums.py` 添加 HypothesisStatus 枚举
- [x] Task 2: 创建 `src/discovery/__init__.py` 模块入口
- [x] Task 3: 创建 `src/discovery/pool/models.py` 数据模型（AnomalyEvent, Hypothesis, ValidationResult）
- [x] Task 4: 创建 `src/discovery/pool/manager.py` 候选池管理器
- [x] Task 5: 创建 `src/discovery/pool/__init__.py`

## 阶段 2: 检测器 (P0)

- [x] Task 6: 创建 `src/discovery/factory/detectors/base.py` 检测器基类
- [x] Task 7: 创建 `src/discovery/factory/detectors/volatility.py` 波动率检测器
- [x] Task 8: 创建 `src/discovery/factory/detectors/__init__.py`
- [x] Task 9: 创建 `src/discovery/factory/engine.py` 工厂引擎
- [x] Task 10: 创建 `src/discovery/factory/__init__.py`

## 阶段 3: 验证器 (P1)

- [x] Task 11: 创建 `src/discovery/validator/engine.py` 验证引擎（复用 learning/statistics.py）
- [x] Task 12: 创建 `src/discovery/validator/__init__.py`

## 阶段 4: 晋升器 (P1)

- [x] Task 13: 创建 `src/discovery/promoter/generator.py` 证人生成器（复用 strategy/base.py）
- [x] Task 14: 创建 `src/discovery/promoter/__init__.py`

## 阶段 5: 更多检测器 (P2)

- [x] Task 15: 创建 `src/discovery/factory/detectors/volume.py` 成交量检测器
- [x] Task 16: 创建 `src/discovery/factory/detectors/funding.py` 资金费率检测器
- [x] Task 17: 创建 `src/discovery/factory/detectors/liquidation.py` 清算检测器

## 阶段 6: 测试 (P1)

- [x] Task 18: 创建 `tests/unit/discovery/test_models.py`
- [x] Task 19: 创建 `tests/unit/discovery/test_pool_manager.py`
- [x] Task 20: 创建 `tests/unit/discovery/test_detectors.py`
- [x] Task 21: 创建 `tests/unit/discovery/test_validator.py`
- [x] Task 22: 创建 `tests/unit/discovery/test_generator.py`
- [x] Task 23: 创建 `tests/integration/test_discovery_flow.py`

## 阶段 7: API 集成 (P2)

- [x] Task 24: 创建 `src/api/routes/discovery.py` API 路由
- [x] Task 25: 更新 `src/api/app.py` 注册路由

## 完成状态 ✅

全部 25 个任务已完成，323 个测试通过。
