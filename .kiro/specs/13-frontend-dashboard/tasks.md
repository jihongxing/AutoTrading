# Dashboard 与 Trading 页面任务

## Task 1: WebSocket 基础设施
- [x] 1.1 创建 src/hooks/useWebSocket.ts - WebSocket Hook
- [x] 1.2 实现连接管理（connect/disconnect）
- [x] 1.3 实现自动重连机制
- [x] 1.4 实现心跳检测（ping/pong）
- [x] 1.5 实现频道订阅/取消订阅
- [x] 1.6 创建 src/stores/wsStore.ts - 连接状态管理

## Task 2: Trading API 封装
- [x] 2.1 创建 src/api/trading.ts - 交易接口
- [x] 2.2 创建 src/api/market.ts - 行情接口
- [x] 2.3 创建 src/api/system.ts - 系统状态接口
- [x] 2.4 定义接口响应类型

## Task 3: 状态管理
- [x] 3.1 创建 src/stores/tradingStore.ts - 交易状态
- [x] 3.2 创建 src/stores/systemStore.ts - 系统状态
- [x] 3.3 创建 src/stores/riskStore.ts - 风控状态
- [x] 3.4 实现 WebSocket 消息处理逻辑

## Task 4: 通用图表组件
- [x] 4.1 安装 recharts 依赖
- [x] 4.2 创建 src/components/charts/PnLChart.tsx - 收益曲线
- [x] 4.3 创建 src/components/charts/ProgressBar.tsx - 进度条
- [x] 4.4 创建 src/utils/format.ts - 数字/时间格式化

## Task 5: Dashboard 组件
- [x] 5.1 创建 src/components/dashboard/StatCard.tsx - 统计卡片
- [x] 5.2 创建 src/components/dashboard/PositionCard.tsx - 持仓卡片
- [x] 5.3 创建 src/components/dashboard/OrderList.tsx - 订单列表
- [x] 5.4 创建 src/components/dashboard/RiskOverview.tsx - 风控概览
- [x] 5.5 创建 src/components/dashboard/SystemStatus.tsx - 系统状态

## Task 6: Dashboard 页面
- [x] 6.1 实现 DashboardPage 桌面端布局
- [x] 6.2 实现 DashboardPage 移动端布局
- [x] 6.3 集成 WebSocket 实时更新
- [x] 6.4 实现数据加载状态
- [x] 6.5 实现错误处理

## Task 7: K线图组件
- [x] 7.1 安装 lightweight-charts 依赖
- [x] 7.2 创建 src/components/charts/KlineChart.tsx
- [x] 7.3 实现周期切换（1m/5m/15m/1h/4h/1d）
- [x] 7.4 实现交易标记显示
- [x] 7.5 实现移动端全屏模式

## Task 8: Trading 组件
- [x] 8.1 创建 src/components/trading/PositionDetail.tsx - 持仓详情
- [x] 8.2 创建 src/components/trading/ActiveOrders.tsx - 活跃订单
- [x] 8.3 创建 src/components/trading/OrderHistory.tsx - 历史订单
- [x] 8.4 实现订单撤销功能
- [x] 8.5 实现分页加载

## Task 9: Trading 页面
- [x] 9.1 实现 TradingPage 桌面端布局
- [x] 9.2 实现 TradingPage 移动端布局
- [x] 9.3 集成 K线图 WebSocket 数据
- [x] 9.4 集成订单/持仓 WebSocket 更新

## Task 10: 测试与优化
- [x] 10.1 测试 WebSocket 连接稳定性
- [x] 10.2 测试断线重连
- [x] 10.3 测试数据实时更新
- [x] 10.4 测试移动端响应式
- [x] 10.5 性能优化（防抖/节流）
