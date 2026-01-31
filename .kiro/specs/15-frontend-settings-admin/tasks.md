# Settings 与 Admin 页面任务

## Task 1: API 封装
- [x] 1.1 扩展 src/api/user.ts - 用户设置接口
- [x] 1.2 创建 src/api/admin.ts - 管理接口
- [x] 1.3 定义响应类型

## Task 2: Settings 组件
- [x] 2.1 创建 src/components/settings/AccountInfo.tsx - 账户信息
- [x] 2.2 创建 src/components/settings/ExchangeConfig.tsx - 交易所配置
- [x] 2.3 创建 src/components/settings/ExchangeForm.tsx - 配置表单
- [x] 2.4 创建 src/components/settings/NotificationSettings.tsx - 通知设置
- [x] 2.5 创建 src/components/settings/PasswordChangeModal.tsx - 修改密码

## Task 3: Settings 页面
- [x] 3.1 实现 SettingsPage 桌面端布局
- [x] 3.2 实现 SettingsPage 移动端布局
- [x] 3.3 实现 API Key 添加/验证流程
- [x] 3.4 实现密码修改流程
- [x] 3.5 实现删除确认弹窗

## Task 4: Admin 组件
- [x] 4.1 创建 src/components/admin/PlatformStats.tsx - 平台统计
- [x] 4.2 创建 src/components/admin/UserTable.tsx - 用户表格
- [x] 4.3 创建 src/components/admin/UserDetail.tsx - 用户详情
- [x] 4.4 创建 src/components/admin/SystemActions.tsx - 系统操作

## Task 5: Admin 页面
- [x] 5.1 实现 AdminPage 布局（仅桌面端）
- [x] 5.2 实现用户搜索/筛选
- [x] 5.3 实现分页
- [x] 5.4 实现用户状态管理
- [x] 5.5 实现强制锁定功能

## Task 6: 权限控制
- [x] 6.1 创建 src/hooks/usePermission.ts - 权限 Hook
- [x] 6.2 创建 src/components/AdminRoute.tsx - 管理员路由守卫
- [x] 6.3 更新路由配置添加 Admin 路由

## Task 7: 移动端优化
- [x] 7.1 完善 TabBar 组件样式
- [x] 7.2 创建 src/components/ui/Skeleton.tsx - 骨架屏
- [x] 7.3 创建 src/components/ui/PullToRefresh.tsx - 下拉刷新
- [x] 7.4 优化触摸区域（最小 44x44px）

## Task 8: 通用组件补充
- [x] 8.1 创建 src/components/ui/Table.tsx - 表格组件
- [x] 8.2 创建 src/components/ui/Pagination.tsx - 分页组件
- [x] 8.3 创建 src/components/ui/Select.tsx - 下拉选择
- [x] 8.4 创建 src/components/ui/Switch.tsx - 开关组件

## Task 9: 表单验证
- [x] 9.1 安装 react-hook-form + zod（使用内置验证替代）
- [x] 9.2 创建表单验证 schema（内置于组件）
- [x] 9.3 实现表单错误提示

## Task 10: 测试与优化
- [x] 10.1 测试 API Key 配置流程
- [x] 10.2 测试密码修改流程
- [x] 10.3 测试管理员功能
- [x] 10.4 测试移动端体验
- [x] 10.5 性能优化（懒加载、代码分割）
