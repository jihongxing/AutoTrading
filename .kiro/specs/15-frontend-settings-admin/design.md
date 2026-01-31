# Settings 与 Admin 页面设计

## Settings 页面布局

```
┌─────────────────────────────────────────┐
│  账户信息                                │
│  邮箱: user@example.com                 │
│  订阅: PRO (到期: 2026-02-28)           │
│  [修改密码]  [升级订阅]                  │
├─────────────────────────────────────────┤
│  交易所配置                              │
│  Binance API                            │
│  状态: 🟢 已验证                         │
│  API Key: ****...****ABCD               │
│  [重新验证]  [修改]  [删除]              │
├─────────────────────────────────────────┤
│  通知设置                                │
│  ☑️ 交易执行通知                         │
│  ☑️ 风控警告通知                         │
│  ☐ 每日收益报告                         │
└─────────────────────────────────────────┘
```

## 组件设计

### AccountInfo 账户信息
```typescript
interface AccountInfoProps {
  user: {
    email: string;
    subscription: string;
    trialEndsAt?: string;
    createdAt: string;
  };
  onChangePassword: () => void;
}
```

### ExchangeConfig 交易所配置
```typescript
interface ExchangeConfig {
  exchange: string;
  apiKeyMasked: string;    // ****ABCD
  isValid: boolean;
  lastVerifiedAt?: string;
  testnet: boolean;
  leverage: number;
  maxPositionPct: number;
}

interface ExchangeConfigFormData {
  apiKey: string;
  apiSecret: string;
  testnet: boolean;
  leverage: number;
  maxPositionPct: number;
}
```

### PasswordChangeModal 修改密码弹窗
```typescript
interface PasswordChangeData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}
```

### AdminUserTable 用户管理表格
```typescript
interface AdminUser {
  userId: string;
  email: string;
  status: 'pending' | 'active' | 'suspended' | 'banned';
  subscription: string;
  createdAt: string;
  lastLoginAt?: string;
}
```

## API 接口

```typescript
// api/user.ts (扩展)
export const userApi = {
  getMe: () => apiClient.get('/users/me'),
  updateMe: (data: Partial<User>) => apiClient.put('/users/me', data),
  changePassword: (data: PasswordChangeData) => 
    apiClient.put('/users/me/password', data),
  
  // 交易所配置
  getExchange: () => apiClient.get('/users/me/exchange'),
  updateExchange: (data: ExchangeConfigFormData) => 
    apiClient.put('/users/me/exchange', data),
  verifyExchange: () => apiClient.post('/users/me/exchange/verify'),
  deleteExchange: () => apiClient.delete('/users/me/exchange'),
};

// api/admin.ts
export const adminApi = {
  getStats: () => apiClient.get('/admin/stats'),
  getUsers: (params?: { search?: string; status?: string; page?: number }) =>
    apiClient.get('/admin/users', { params }),
  getUser: (id: string) => apiClient.get(`/admin/users/${id}`),
  suspendUser: (id: string, reason: string) =>
    apiClient.post(`/admin/users/${id}/suspend`, { reason }),
  activateUser: (id: string) =>
    apiClient.post(`/admin/users/${id}/activate`),
  forceLock: (reason: string) =>
    apiClient.post('/api/v1/state/force-lock', { reason }),
};
```

## Admin 页面布局

```
┌─────────┬─────────┬─────────┬─────────┐
│总用户数 │活跃用户 │总交易量 │平台收益 │
└─────────┴─────────┴─────────┴─────────┘
┌─────────────────────────────────────────┐
│  用户管理                                │
│  搜索: [____________] [筛选: 全部 ▼]    │
│  ┌─────────────────────────────────────┐│
│  │ ID | 邮箱 | 状态 | 订阅 | 操作      ││
│  │ ...                                 ││
│  └─────────────────────────────────────┘│
│  [< 上一页] 第 1/10 页 [下一页 >]       │
├─────────────────────────────────────────┤
│  系统操作                                │
│  [强制锁定系统]  [查看审计日志]          │
└─────────────────────────────────────────┘
```

## 移动端优化

### 底部 Tab 导航
```typescript
const TABS = [
  { path: '/dashboard', icon: HomeIcon, label: 'Dashboard' },
  { path: '/trading', icon: ChartIcon, label: 'Trading' },
  { path: '/risk', icon: ShieldIcon, label: 'Risk' },
  { path: '/settings', icon: SettingsIcon, label: 'Settings' },
];
```

### 骨架屏组件
```typescript
interface SkeletonProps {
  variant: 'text' | 'card' | 'chart' | 'table';
  lines?: number;
}
```

### 下拉刷新
```typescript
interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  children: ReactNode;
}
```

## 权限控制

```typescript
// hooks/usePermission.ts
const usePermission = () => {
  const { user } = useAuthStore();
  
  return {
    isAdmin: user?.isAdmin ?? false,
    canManageUsers: user?.isAdmin ?? false,
    canForceLock: user?.isAdmin ?? false,
  };
};

// components/AdminRoute.tsx
const AdminRoute = ({ children }) => {
  const { isAdmin } = usePermission();
  
  if (!isAdmin) {
    return <Navigate to="/dashboard" />;
  }
  
  return children;
};
```
