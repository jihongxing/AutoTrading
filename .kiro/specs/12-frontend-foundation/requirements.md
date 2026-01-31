# 前端基础架构需求

## 概述
搭建前端项目基础架构，包括技术栈初始化、路由配置、认证流程和基础 UI 组件。

## 功能需求

### FR-1: 项目初始化
- FR-1.1: 使用 Vite + React 18 + TypeScript 创建项目
- FR-1.2: 配置 TailwindCSS 样式框架
- FR-1.3: 配置 ESLint + Prettier 代码规范
- FR-1.4: 配置路径别名 (@/)

### FR-2: 状态管理与请求
- FR-2.1: 配置 Zustand 状态管理
- FR-2.2: 配置 Axios 请求客户端，统一错误处理
- FR-2.3: 配置 TanStack Query 数据缓存
- FR-2.4: 实现 JWT Token 自动刷新机制

### FR-3: 路由与布局
- FR-3.1: 配置 React Router v6 路由
- FR-3.2: 实现主布局组件（顶部导航 + 内容区）
- FR-3.3: 实现移动端布局（底部 Tab 导航）
- FR-3.4: 实现路由守卫（未登录跳转登录页）

### FR-4: 认证页面
- FR-4.1: 实现登录页面
- FR-4.2: 实现注册页面
- FR-4.3: 实现忘记密码页面（可选）
- FR-4.4: 实现认证状态持久化

### FR-5: 基础 UI 组件
- FR-5.1: Button 按钮组件
- FR-5.2: Input 输入框组件
- FR-5.3: Card 卡片组件
- FR-5.4: Loading 加载组件
- FR-5.5: Toast 提示组件

## 非功能需求

### NFR-1: 响应式设计
- 支持桌面端 (≥1024px) 和移动端 (<1024px)
- 移动端优先设计原则

### NFR-2: 性能
- 首屏加载 < 3s
- 代码分割，按需加载

### NFR-3: 安全
- Token 存储在 memory，refresh_token 存储在 httpOnly cookie（或 localStorage）
- 敏感操作需要二次确认

## 参考文档
- #[[file:docs/01-系统设计/前端可视化PRD.md]]
