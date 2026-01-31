# 前端基础架构任务

## Task 1: 项目初始化
- [x] 1.1 使用 Vite 创建 React + TypeScript 项目
- [x] 1.2 安装依赖：tailwindcss, postcss, autoprefixer
- [x] 1.3 配置 tailwind.config.js
- [x] 1.4 配置 tsconfig.json 路径别名
- [x] 1.5 配置 vite.config.ts
- [x] 1.6 创建 .env.example 环境变量模板

## Task 2: 安装核心依赖
- [x] 2.1 安装 react-router-dom
- [x] 2.2 安装 zustand
- [x] 2.3 安装 @tanstack/react-query
- [x] 2.4 安装 axios
- [x] 2.5 安装 clsx, tailwind-merge (样式工具)

## Task 3: API 客户端
- [x] 3.1 创建 src/api/client.ts - Axios 实例
- [x] 3.2 实现请求拦截器 - 添加 Authorization Header
- [x] 3.3 实现响应拦截器 - 401 处理和 Token 刷新
- [x] 3.4 创建 src/api/types.ts - API 响应类型定义
- [x] 3.5 创建 src/api/auth.ts - 认证接口封装

## Task 4: 状态管理
- [x] 4.1 创建 src/stores/authStore.ts - 认证状态
- [x] 4.2 实现 login/logout/setTokens 方法
- [x] 4.3 配置 persist 中间件持久化
- [x] 4.4 创建 src/hooks/useAuth.ts - 认证 Hook

## Task 5: 基础 UI 组件
- [x] 5.1 创建 src/components/ui/Button.tsx
- [x] 5.2 创建 src/components/ui/Input.tsx
- [x] 5.3 创建 src/components/ui/Card.tsx
- [x] 5.4 创建 src/components/ui/Loading.tsx
- [x] 5.5 创建 src/components/ui/Toast.tsx
- [x] 5.6 创建 src/components/ui/index.ts 统一导出

## Task 6: 布局组件
- [x] 6.1 创建 src/components/layout/Navbar.tsx - 顶部导航
- [x] 6.2 创建 src/components/layout/TabBar.tsx - 底部 Tab
- [x] 6.3 创建 src/components/layout/MainLayout.tsx - 桌面布局
- [x] 6.4 创建 src/components/layout/MobileLayout.tsx - 移动端布局
- [x] 6.5 创建 src/hooks/useMediaQuery.ts - 响应式 Hook

## Task 7: 路由配置
- [x] 7.1 创建 src/routes.tsx - 路由定义
- [x] 7.2 创建 src/components/ProtectedRoute.tsx - 路由守卫
- [x] 7.3 配置 TanStack Query Provider
- [x] 7.4 更新 src/App.tsx - 整合路由和 Provider

## Task 8: 认证页面
- [x] 8.1 创建 src/features/auth/LoginPage.tsx
- [x] 8.2 创建 src/features/auth/RegisterPage.tsx
- [x] 8.3 实现表单验证
- [x] 8.4 实现登录/注册 API 调用
- [x] 8.5 实现错误提示

## Task 9: 占位页面
- [x] 9.1 创建 src/features/dashboard/DashboardPage.tsx (占位)
- [x] 9.2 创建 src/features/trading/TradingPage.tsx (占位)
- [x] 9.3 创建 src/features/risk/RiskPage.tsx (占位)
- [x] 9.4 创建 src/features/strategy/StrategyPage.tsx (占位)
- [x] 9.5 创建 src/features/settings/SettingsPage.tsx (占位)

## Task 10: 测试与验证
- [x] 10.1 验证构建成功
- [x] 10.2 验证路由配置
- [x] 10.3 验证 TypeScript 类型检查
- [ ] 10.4 验证路由守卫（需后端配合）
- [ ] 10.5 验证响应式布局切换（需运行时测试）
