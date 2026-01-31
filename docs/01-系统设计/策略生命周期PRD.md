# BTC 自动交易系统 — 策略生命周期管理 PRD

> **核心目标**：建立策略从发现到废弃的完整生命周期管理，支持动态权重调整，最大复用现有实现。

## 一、核心概念

### 1.1 策略 = 证人

- 代码中统一使用 `BaseStrategy` 作为基类
- `WitnessRegistry` 管理所有证人/策略
- 每个证人输出 `Claim`，不直接下单

### 1.2 证人分级（TIER）

| TIER | 角色 | 说明 |
|------|------|------|
| TIER_1 | 核心证人 | 决定交易方向，高发言权 |
| TIER_2 | 辅助证人 | 提供加权支持或反对 |
| TIER_3 | 否决证人 | 一票否决权，系统级保护 |

### 1.3 新策略晋升 TIER 规则

```
假设工厂发现 → 验证通过 → 晋升为 TIER_2 辅助证人
                              ↓
                    表现优异 → 人工审批升级为 TIER_1
```

- 新策略默认晋升为 **TIER_2**
- TIER_1 需长期验证后人工审批
- TIER_3 是系统级，不自动生成

## 二、动态权重系统

### 2.1 权重模型

```python
@dataclass
class WitnessWeight:
    strategy_id: str
    base_weight: float = 1.0      # 基础权重 (L1 配置)
    health_factor: float = 1.0    # 健康度因子 (0.5-1.2)
    learning_factor: float = 1.0  # 自学习因子 (0.8-1.2)
    
    @property
    def effective_weight(self) -> float:
        return self.base_weight * self.health_factor * self.learning_factor
```

### 2.2 权重因子来源

| 因子 | 来源 | 更新频率 | 范围 |
|------|------|----------|------|
| base_weight | config/strategy.yaml (L1) | 人工修改 | 0.5-2.0 |
| health_factor | HealthManager | 每小时 | 0.5-1.2 |
| learning_factor | LearningEngine | 每周 | 0.8-1.2 |

### 2.3 健康度 → 权重映射

| 健康度等级 | health_factor |
|------------|---------------|
| A (优秀) | 1.2 |
| B (良好) | 1.0 |
| C (警告) | 0.7 |
| D (危险) | 0.5 |

### 2.4 聚合逻辑改造

```python
# 现有（硬编码）
base += claim.confidence * 0.1

# 改为（动态权重）
weight = self.weight_manager.get_weight(claim.strategy_id)
base += claim.confidence * weight.effective_weight * TIER2_BASE_FACTOR
```

## 三、生命周期状态

```
发现 → 验证 → 影子 → 正式 → 降权 → 废弃
NEW   TESTING  SHADOW  ACTIVE  DEGRADED  RETIRED
```

| 状态 | 所属池 | 说明 |
|------|--------|------|
| NEW | 候选池 | 检测器发现的新假设 |
| TESTING | 验证池 | 回测验证中 |
| SHADOW | 影子池 | 模拟运行，不参与决策 |
| ACTIVE | 主策略池 | 正式参与交易决策 |
| DEGRADED | 降权池 | 健康度下降，权重降低 |
| RETIRED | 废弃池 | 归档，不再使用 |

## 四、状态流转规则

### 4.1 晋升条件

| 转换 | 条件 | 触发 | 晋升 TIER |
|------|------|------|-----------|
| NEW → TESTING | 假设生成完成 | 自动 | - |
| TESTING → SHADOW | 胜率 ≥ 51%，样本 ≥ 100 | 自动 | - |
| SHADOW → ACTIVE | 影子运行 7 天，胜率稳定 | 人工审批 | TIER_2 |
| TIER_2 → TIER_1 | 运行 30 天，健康度 A | 人工审批 | TIER_1 |

### 4.2 降级条件

| 转换 | 条件 | 触发 |
|------|------|------|
| ACTIVE → DEGRADED | 健康度 < C 级 | 自动 |
| DEGRADED → RETIRED | 30 天内未恢复 | 自动 |
| DEGRADED → ACTIVE | 健康度恢复至 B 级 | 自动 |

### 4.3 特殊规则

- TIER_3 否决证人不参与生命周期管理
- RETIRED 策略保留历史数据，不可恢复

## 五、现有模块复用

| 模块 | 位置 | 复用方式 |
|------|------|----------|
| HypothesisPoolManager | `discovery/pool/` | 扩展 SHADOW 状态 |
| HypothesisValidator | `discovery/validator/` | 直接复用 |
| WitnessGenerator | `discovery/promoter/` | 直接复用 |
| WitnessRegistry | `strategy/registry.py` | 扩展状态和权重 |
| HealthManager | `strategy/health.py` | 驱动降级和权重 |
| LearningEngine | `learning/engine.py` | 优化 learning_factor |

## 六、架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    StrategyPoolManager                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │     HypothesisPoolManager (候选池)                   │    │
│  │     NEW → TESTING → SHADOW                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                              ↓ 晋升为 TIER_2                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │     WitnessRegistry (主策略池)                       │    │
│  │     ACTIVE ←→ DEGRADED → RETIRED                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                              ↑                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │     WeightManager (权重管理)                         │    │
│  │     base × health_factor × learning_factor          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 七、API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/lifecycle/strategies` | GET | 获取所有策略状态 |
| `/api/v1/lifecycle/{id}/promote` | POST | 手动晋升 |
| `/api/v1/lifecycle/{id}/demote` | POST | 手动降级 |
| `/api/v1/lifecycle/{id}/retire` | POST | 手动废弃 |
| `/api/v1/lifecycle/{id}/upgrade-tier` | POST | 升级 TIER（需审批） |
| `/api/v1/weights` | GET | 获取所有权重 |
| `/api/v1/weights/{id}` | PUT | 修改基础权重 |

## 八、实现优先级

1. **Phase 1**：动态权重系统（WeightManager）
2. **Phase 2**：扩展状态枚举和 Registry
3. **Phase 3**：StrategyPoolManager 统一管理
4. **Phase 4**：ShadowRunner 影子运行
5. **Phase 5**：API 和定时任务

## 九、成功标准

- [ ] 权重动态计算，无硬编码
- [ ] 新策略默认 TIER_2
- [ ] 健康度驱动权重和降级
- [ ] 自学习优化 learning_factor
- [ ] 策略状态可追溯
