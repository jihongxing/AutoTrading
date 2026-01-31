# 策略生命周期管理 - 需求文档

## 概述

建立策略从发现到废弃的完整生命周期管理系统，支持动态权重调整，最大复用现有实现。

## 用户故事

### US-1: 动态权重
作为系统，我需要根据健康度和学习结果动态调整证人权重，以优化交易决策。

**验收标准：**
- AC-1.1: 权重 = base_weight × health_factor × learning_factor
- AC-1.2: health_factor 根据健康度等级自动更新（A=1.2, B=1.0, C=0.7, D=0.5）
- AC-1.3: learning_factor 由 LearningEngine 每周更新
- AC-1.4: base_weight 可通过配置文件修改

### US-2: 策略状态追踪
作为系统管理员，我需要查看所有策略的当前状态，以便了解策略池的整体情况。

**验收标准：**
- AC-2.1: 可查询策略当前状态（NEW/TESTING/SHADOW/ACTIVE/DEGRADED/RETIRED）
- AC-2.2: 可按状态筛选策略列表
- AC-2.3: 可查看策略状态变更历史

### US-3: 自动晋升
作为系统，我需要自动将满足条件的策略晋升到下一阶段。

**验收标准：**
- AC-3.1: NEW → TESTING：假设生成后自动进入验证
- AC-3.2: TESTING → SHADOW：回测胜率 ≥ 51%，样本 ≥ 100 时自动晋升
- AC-3.3: SHADOW → ACTIVE：需人工审批，晋升后默认 TIER_2
- AC-3.4: TIER_2 → TIER_1：需人工审批，运行 30 天且健康度 A

### US-4: 自动降级
作为系统，我需要自动将健康度下降的策略降级，以保护交易资金。

**验收标准：**
- AC-4.1: ACTIVE → DEGRADED：健康度 < C 级时自动降级
- AC-4.2: DEGRADED → RETIRED：30 天内未恢复自动废弃
- AC-4.3: DEGRADED → ACTIVE：健康度恢复至 B 级以上自动恢复

### US-5: 影子运行
作为系统，我需要对 SHADOW 状态的策略进行模拟运行，以验证其实际表现。

**验收标准：**
- AC-5.1: SHADOW 策略接收市场数据并生成 Claim
- AC-5.2: Claim 被记录但不参与实际交易决策
- AC-5.3: 可查询影子运行的模拟绩效

### US-6: 手动管理
作为系统管理员，我需要手动管理策略状态和权重。

**验收标准：**
- AC-6.1: 可手动修改 base_weight
- AC-6.2: 可手动晋升/降级策略
- AC-6.3: 可手动升级 TIER（TIER_2 → TIER_1）
- AC-6.4: TIER_3 否决证人不可被修改

## 功能需求

### FR-1: WeightManager
- 管理所有证人的权重配置
- 计算 effective_weight
- 与 HealthManager 和 LearningEngine 集成

### FR-2: 统一状态枚举
- 扩展现有 HypothesisStatus，新增 SHADOW、ACTIVE、DEGRADED、RETIRED 状态
- 保持向后兼容

### FR-3: StrategyPoolManager
- 统一管理 HypothesisPoolManager 和 WitnessRegistry
- 提供状态查询和流转接口
- 定期执行生命周期检查

### FR-4: ShadowRunner
- 对 SHADOW 策略进行模拟运行
- 记录模拟交易结果
- 计算模拟绩效指标

### FR-5: 聚合逻辑改造
- 移除硬编码权重（0.1、0.05）
- 使用 WeightManager 获取动态权重

### FR-6: REST API
- 状态查询接口
- 权重管理接口
- 手动管理接口

## 非功能需求

### NFR-1: 复用现有实现
- 复用 HypothesisPoolManager 管理候选池
- 复用 HypothesisValidator 进行回测验证
- 复用 WitnessRegistry 管理主策略池
- 复用 HealthManager 驱动降级和权重
- 复用 LearningEngine 优化 learning_factor

### NFR-2: 参数分层
- base_weight 属于 L1（配置文件）
- health_factor 属于 L3（自动计算）
- learning_factor 属于 L3（自学习）

## 约束

- TIER_3 否决证人不参与生命周期管理
- 新策略晋升后默认 TIER_2
- TIER_1 升级需人工审批
- RETIRED 状态不可恢复
