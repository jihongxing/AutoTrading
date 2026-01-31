# 策略生命周期管理 - 任务清单

## Phase 1: 动态权重系统

### Task 1.1: 创建权重模型
- [x] 创建 `src/strategy/lifecycle/__init__.py`
- [x] 创建 `src/strategy/lifecycle/models.py`
- [x] 定义 `WitnessWeight` 数据类
- [x] 定义 `HEALTH_FACTOR_MAP` 映射
- [x] 定义 `StrategyStateRecord` 状态记录

### Task 1.2: 实现 WeightManager
- [x] 创建 `src/strategy/lifecycle/weight.py`
- [x] 实现 `__init__()` 加载配置
- [x] 实现 `get_weight()` 获取权重（含 health_factor 更新）
- [x] 实现 `set_base_weight()` 设置基础权重
- [x] 实现 `set_learning_factor()` 设置学习因子
- [x] 实现 `_load_base_weights()` 从配置加载

### Task 1.3: 创建权重配置文件
- [x] 创建 `config/strategy.yaml`
- [x] 配置现有 8 个证人的 base_weight
- [x] 配置 tier2_base_factor 和 confidence_threshold

### Task 1.4: 改造 StrategyOrchestrator
- [x] 在 `src/strategy/orchestrator.py` 注入 WeightManager
- [x] 改造 `_calculate_total_confidence()` 使用动态权重
- [x] 移除硬编码的 0.1 和 0.05

## Phase 2: 状态枚举和模型

### Task 2.1: 扩展状态枚举
- [x] 在 `src/common/enums.py` 新增 `StrategyStatus` 枚举
- [x] 包含: NEW, TESTING, SHADOW, ACTIVE, DEGRADED, RETIRED
- [x] 保持与 HypothesisStatus 的兼容映射

### Task 2.2: 扩展 WitnessRegistry
- [x] 在 `src/strategy/registry.py` 新增 `_status` 字段
- [x] 新增 `_tier` 字段（支持动态 TIER）
- [x] 实现 `set_status()` 方法
- [x] 实现 `get_status()` 方法
- [x] 实现 `is_protected()` 方法（TIER_3 保护）

### Task 2.3: 扩展 HypothesisPoolManager
- [x] 在 `src/discovery/pool/manager.py` 支持 SHADOW 状态
- [x] 新增 `get_shadow_hypotheses()` 方法
- [x] 新增 `promote_to_shadow()` 方法

## Phase 3: StrategyPoolManager

### Task 3.1: 实现核心管理器
- [x] 创建 `src/strategy/lifecycle/manager.py`
- [x] 实现 `__init__()` 整合现有管理器
- [x] 实现 `get_status()` 状态查询
- [x] 实现 `get_all_by_status()` 批量查询
- [x] 实现 `get_state_history()` 历史查询

### Task 3.2: 实现晋升逻辑
- [x] 实现 `promote()` 统一晋升入口
- [x] 实现 `_promote_to_testing()` NEW → TESTING
- [x] 实现 `_promote_to_shadow()` TESTING → SHADOW
- [x] 实现 `_promote_to_active()` SHADOW → ACTIVE（默认 TIER_2）
- [x] 实现 `upgrade_tier()` TIER_2 → TIER_1（需审批）

### Task 3.3: 实现降级逻辑
- [x] 实现 `demote()` 统一降级入口
- [x] 实现 `retire()` 废弃策略
- [x] 实现 `check_demotions()` 自动降级检查
- [x] 实现 `cleanup_retired()` 清理过期废弃策略

## Phase 4: 影子运行

### Task 4.1: 实现 ShadowRunner
- [x] 创建 `src/strategy/lifecycle/shadow.py`
- [x] 实现 `run_all()` 运行所有 SHADOW 策略
- [x] 实现 `_record_trade()` 记录影子交易
- [x] 实现 `get_performance()` 获取绩效
- [x] 实现 `is_ready_for_promotion()` 检查晋升条件

## Phase 5: API 接口

### Task 5.1: 生命周期 API
- [x] 创建 `src/api/routes/lifecycle.py`
- [x] 实现 `GET /strategies` 获取所有策略状态
- [x] 实现 `GET /strategies/{id}` 获取单个策略
- [x] 实现 `POST /strategies/{id}/promote` 手动晋升
- [x] 实现 `POST /strategies/{id}/demote` 手动降级
- [x] 实现 `POST /strategies/{id}/upgrade-tier` 升级 TIER

### Task 5.2: 权重 API
- [x] 实现 `GET /weights` 获取所有权重
- [x] 实现 `GET /weights/{id}` 获取单个权重
- [x] 实现 `PUT /weights/{id}` 修改基础权重

### Task 5.3: 注册路由
- [x] 在 `src/api/app.py` 注册 lifecycle 路由

## Phase 6: 集成 LearningEngine

### Task 6.1: 扩展 LearningEngine
- [x] 在 `src/learning/engine.py` 新增权重优化
- [x] 实现 `optimize_weights()` 方法
- [x] 调用 `weight_manager.set_learning_factor()`
- [x] 添加到每周学习任务

## Phase 7: 测试

### Task 7.1: 权重测试
- [x] 创建 `tests/unit/strategy/lifecycle/__init__.py`
- [x] 创建 `tests/unit/strategy/lifecycle/test_weight.py`
- [x] 测试 effective_weight 计算
- [x] 测试 health_factor 映射
- [x] 测试边界值限制

### Task 7.2: 管理器测试
- [x] 创建 `tests/unit/strategy/lifecycle/test_manager.py`
- [x] 测试状态查询
- [x] 测试晋升逻辑
- [x] 测试降级逻辑
- [x] 测试 TIER 升级

### Task 7.3: 影子运行测试
- [x] 创建 `tests/unit/strategy/lifecycle/test_shadow.py`
- [x] 测试策略注册/注销
- [x] 测试影子交易记录
- [x] 测试绩效计算
- [x] 测试晋升条件检查

### Task 7.4: 集成测试
- [x] 创建 `tests/integration/test_lifecycle_flow.py`
- [x] 测试完整生命周期流程
- [x] 测试权重与健康度联动

## 任务依赖

```
Phase 1 (动态权重) ✅
    ↓
Phase 2 (状态枚举) ✅
    ↓
Phase 3 (PoolManager) ✅
    ↓
Phase 4 (影子运行) ✅
    ↓
Phase 5 (API) ✅
    ↓
Phase 6 (Learning 集成) ✅
    ↓
Phase 7 (测试) ✅
```

## 复用清单

| 任务 | 复用模块 | 复用方式 |
|------|----------|----------|
| Task 1.2 | HealthManager | 读取健康度 |
| Task 2.3 | HypothesisPoolManager | 扩展方法 |
| Task 3.2 | HypothesisValidator | 调用验证结果 |
| Task 3.2 | WitnessGenerator | 生成证人代码 |
| Task 4.1 | BaseStrategy.generate_claim() | 直接调用 |
| Task 6.1 | LearningEngine | 扩展优化逻辑 |
