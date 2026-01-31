# 前端基础架构设计

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.x | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Vite | 5.x | 构建工具 |
| TailwindCSS | 3.x | 样式框架 |
| React Router | 6.x | 路由 |
| Zustand | 4.x | 状态管理 |
| TanStack Query | 5.x | 数据请求 |
| Axios | 1.x | HTTP 客户端 |

## 项目结构

```
frontend/
├── public/
├── src/
│   ├── api/                 # API 请求
│   │   ├── client.ts        # Axios 实例
│   │   ├── auth.ts          # 认证接口
│   │   └── types.ts         # API 类型
│   ├── components/          # 通用组件
│   │   ├── ui/              # 基础 UI
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   └── index.ts
│   │   └── layout/          # 布局组件
│   │       ├── MainLayout.tsx
│   │       ├── MobileLayout.tsx
│   │       ├── Navbar.tsx
│   │       └── TabBar.tsx
│   ├── features/            # 功能模块
│   │   └── auth/            # 认证模块
│   │       ├── LoginPage.tsx
│   │       ├── RegisterPage.tsx
│   │       └── hooks.ts
│   ├── hooks/               # 通用 Hooks
│   │   ├── useAuth.ts
│   │   └── useMediaQuery.ts
│   ├── stores/              # Zustand 状态
│   │   └── authStore.ts
│   ├── utils/               # 工具函数
│   │   └── storage.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── routes.tsx
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## 认证流程

```
登录流程:
1. 用户输入 email + password
2. POST /auth/login
3. 返回 { access_token, refresh_token }
4. 存储 token 到 authStore
5. 跳转到 Dashboard

Token 刷新:
1. Axios 拦截器检测 401 错误
2. 使用 refresh_token 调用 POST /auth/refresh
3. 更新 access_token
4. 重试原请求
5. 刷新失败 → 清除状态 → 跳转登录页
```

## 路由配置

```typescript
const routes = [
  // 公开路由
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  
  // 受保护路由
  {
    path: '/',
    element: <ProtectedRoute><MainLayout /></ProtectedRoute>,
    children: [
      { path: '', element: <Navigate to="/dashboard" /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'trading', element: <TradingPage /> },
      { path: 'risk', element: <RiskPage /> },
      { path: 'strategy', element: <StrategyPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
];
```

## 响应式断点

```typescript
const breakpoints = {
  sm: 640,   // 手机横屏
  md: 768,   // 平板竖屏
  lg: 1024,  // 平板横屏 / 小桌面
  xl: 1280,  // 桌面
};

// 移动端判断
const isMobile = window.innerWidth < 1024;
```

## API 客户端设计

```typescript
// api/client.ts
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
});

// 请求拦截器 - 添加 Token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器 - 处理 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // 尝试刷新 Token
      const refreshed = await refreshToken();
      if (refreshed) {
        return apiClient(error.config);
      }
      // 刷新失败，跳转登录
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## 状态管理设计

```typescript
// stores/authStore.ts
interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setTokens: (access: string, refresh: string) => void;
}

const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      // ...
    }),
    { name: 'auth-storage' }
  )
);
```
