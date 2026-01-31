# Risk 与 Strategy 页面设计

## Risk 页面布局

### 桌面端
```
┌─────────┬─────────┬─────────┬─────────┐
│ 🟢 正常  │回撤 3.2%│日亏0.5% │连亏 1次 │
└─────────┴─────────┴─────────┴─────────┘
┌─────────────────────────────────────────┐
│           回撤曲线（30天）               │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│           风控事件日志                   │
└─────────────────────────────────────────┘
```

## 组件设计

### RiskGauge 风控仪表
```typescript
interface RiskGaugeProps {
  label: string;
  current: number;
  threshold: number;
  unit?: string;        // '%' | '次'
  warningAt?: number;   // 警告阈值百分比
}
```

### RiskEventLog 事件日志
```typescript
interface RiskEvent {
  eventId: string;
  timestamp: string;
  eventType: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  details?: Record<string, any>;
}
```

### StateMachine 状态机可视化
```typescript
interface StateMachineProps {
  currentState: string;
  stateHistory?: { state: string; timestamp: string }[];
}

const STATES = ['IDLE', 'OBSERVING', 'READY', 'EXECUTING', 'COOLDOWN', 'RISK_LOCKED'];
const TRANSITIONS = [
  { from: 'IDLE', to: 'OBSERVING' },
  { from: 'OBSERVING', to: 'READY' },
  { from: 'READY', to: 'EXECUTING' },
  { from: 'EXECUTING', to: 'IDLE' },
  { from: 'OBSERVING', to: 'COOLDOWN' },
  { from: 'COOLDOWN', to: 'RISK_LOCKED' },
];
```

### WitnessList 证人列表
```typescript
interface Witness {
  witnessId: string;
  tier: 'TIER1' | 'TIER2' | 'TIER3';
  status: 'ACTIVE' | 'MUTED' | 'PROBATION';
  isActive: boolean;
  health?: {
    winRate: number;
    sampleCount: number;
    weight: number;
    grade: string;
  };
}
```

### SuggestionCard 优化建议
```typescript
interface Suggestion {
  suggestionId: string;
  paramName: string;
  currentValue: number;
  suggestedValue: number;
  action: string;
  reason: string;
  confidence: number;
  requiresApproval: boolean;
}
```

## API 接口

```typescript
// api/risk.ts
export const riskApi = {
  getStatus: () => apiClient.get('/api/v1/risk/status'),
  getEvents: (limit?: number) => 
    apiClient.get('/api/v1/risk/events', { params: { limit } }),
};

// api/strategy.ts
export const strategyApi = {
  getState: () => apiClient.get('/api/v1/state'),
  getWitnesses: () => apiClient.get('/api/v1/witnesses'),
  getWitness: (id: string) => apiClient.get(`/api/v1/witnesses/${id}`),
  muteWitness: (id: string) => apiClient.post(`/api/v1/witnesses/${id}/mute`),
  activateWitness: (id: string) => apiClient.post(`/api/v1/witnesses/${id}/activate`),
};

// api/learning.ts
export const learningApi = {
  getReport: (period?: string) => 
    apiClient.get('/api/v1/learning/report', { params: { period } }),
  getSuggestions: (pendingOnly?: boolean) =>
    apiClient.get('/api/v1/learning/suggestions', { params: { pending_only: pendingOnly } }),
  approveSuggestions: (ids: string[], approved: boolean, comment?: string) =>
    apiClient.post('/api/v1/learning/approve', { suggestion_ids: ids, approved, comment }),
};
```

## 状态管理

```typescript
// stores/riskStore.ts
interface RiskState {
  level: string;
  isLocked: boolean;
  lockReason: string | null;
  currentDrawdown: number;
  dailyLoss: number;
  consecutiveLosses: number;
  events: RiskEvent[];
  
  updateMetrics: (data: Partial<RiskState>) => void;
  addEvent: (event: RiskEvent) => void;
}

// stores/strategyStore.ts
interface StrategyState {
  currentState: string;
  witnesses: Witness[];
  
  updateState: (state: string) => void;
  updateWitness: (witness: Witness) => void;
}
```

## 颜色编码

```typescript
const RISK_COLORS = {
  normal: 'text-green-500',    // < 50% 阈值
  warning: 'text-yellow-500',  // 50-80% 阈值
  danger: 'text-red-500',      // > 80% 阈值
  locked: 'text-gray-500',     // 锁定状态
};

const TIER_COLORS = {
  TIER1: 'bg-blue-100 text-blue-800',
  TIER2: 'bg-green-100 text-green-800',
  TIER3: 'bg-red-100 text-red-800',
};
```
