# Risk 与 Strategy 页面任务

## Task 1: API 封装
- [x] 1.1 创建 src/api/risk.ts - 风控接口
- [x] 1.2 创建 src/api/strategy.ts - 策略接口
- [x] 1.3 创建 src/api/learning.ts - 学习接口
- [x] 1.4 定义响应类型

## Task 2: 状态管理扩展
- [x] 2.1 扩展 src/stores/riskStore.ts - 风控详细状态
- [x] 2.2 创建 src/stores/strategyStore.ts - 策略状态
- [x] 2.3 创建 src/stores/learningStore.ts - 学习状态
- [x] 2.4 集成 WebSocket 风控频道更新

## Task 3: Risk 组件
- [x] 3.1 创建 src/components/risk/RiskStatusBadge.tsx - 状态徽章
- [x] 3.2 创建 src/components/risk/RiskGauge.tsx - 风控仪表
- [x] 3.3 创建 src/components/risk/DrawdownChart.tsx - 回撤曲线
- [x] 3.4 创建 src/components/risk/RiskEventLog.tsx - 事件日志
- [x] 3.5 创建 src/components/risk/RiskMetricsGrid.tsx - 指标网格

## Task 4: Risk 页面
- [x] 4.1 实现 RiskPage 桌面端布局
- [x] 4.2 实现 RiskPage 移动端布局
- [x] 4.3 集成 WebSocket 实时更新
- [x] 4.4 实现事件日志分页/筛选

## Task 5: Strategy 组件
- [x] 5.1 创建 src/components/strategy/StateMachine.tsx - 状态机可视化
- [x] 5.2 创建 src/components/strategy/WitnessList.tsx - 证人列表
- [x] 5.3 创建 src/components/strategy/WitnessCard.tsx - 证人卡片
- [x] 5.4 创建 src/components/strategy/WitnessDetail.tsx - 证人详情弹窗
- [x] 5.5 创建 src/components/strategy/ClaimHistory.tsx - Claim 历史

## Task 6: Strategy 页面
- [x] 6.1 实现 StrategyPage 桌面端布局
- [x] 6.2 实现 StrategyPage 移动端布局（简化版）
- [x] 6.3 实现证人静默/激活功能
- [x] 6.4 实现操作确认弹窗

## Task 7: Learning 组件
- [x] 7.1 创建 src/components/learning/ReportOverview.tsx - 报告概览
- [x] 7.2 创建 src/components/learning/SuggestionList.tsx - 建议列表
- [x] 7.3 创建 src/components/learning/SuggestionCard.tsx - 建议卡片
- [x] 7.4 创建 src/components/learning/WitnessRanking.tsx - 证人排名

## Task 8: Learning 页面
- [x] 8.1 实现 LearningPage 桌面端布局
- [x] 8.2 实现 LearningPage 移动端布局（简化版）
- [x] 8.3 实现建议审批功能
- [x] 8.4 实现批量审批

## Task 9: 通用组件
- [x] 9.1 创建 src/components/ui/Badge.tsx - 徽章组件
- [x] 9.2 创建 src/components/ui/Modal.tsx - 弹窗组件
- [x] 9.3 创建 src/components/ui/ConfirmDialog.tsx - 确认对话框
- [x] 9.4 创建 src/components/ui/Tabs.tsx - 标签页组件

## Task 10: 测试
- [x] 10.1 测试风控指标实时更新
- [x] 10.2 测试证人操作流程
- [x] 10.3 测试建议审批流程
- [x] 10.4 测试移动端适配
