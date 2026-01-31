# Dashboard 与 Trading 页面设计

## WebSocket 管理器

```typescript
// hooks/useWebSocket.ts
interface WSConfig {
  url: string;
  channels: string[];
  onMessage: (msg: WSMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface WSMessage {
  channel: string;
  type: string;
  action: string;
  data: any;
  timestamp: string;
}

class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  
  connect(token: string): void;
  disconnect(): void;
  subscribe(channel: string): void;
  unsubscribe(channel: string): void;
  send(message: object): void;
}
```

## Dashboard 布局

### 桌面端 (≥1024px)
```
┌─────────────────────────────────────────────────────────┐
│  账户余额  │  今日 PnL  │  当前持仓  │  系统状态        │
├─────────────────────────────────────────────────────────┤
│                    收益曲线图                            │
├─────────────────────────────┬───────────────────────────┤
│       最近订单               │      风控指标             │
└─────────────────────────────┴───────────────────────────┘
```

### 移动端 (<1024px)
```
┌─────────────────────┐
│  账户余额 + PnL     │
├─────────────────────┤
│  系统状态           │
├─────────────────────┤
│  当前持仓           │
├─────────────────────┤
│  收益曲线（简化）    │
├─────────────────────┤
│  风控指标           │
└─────────────────────┘
```

## 组件设计

### StatCard 统计卡片
```typescript
interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;        // 变化百分比
  changeLabel?: string;   // 如 "今日"
  icon?: ReactNode;
  loading?: boolean;
}
```

### PnLChart 收益曲线
```typescript
interface PnLChartProps {
  data: { date: string; pnl: number }[];
  period: '7d' | '30d' | 'all';
  onPeriodChange: (period: string) => void;
}
```

### PositionCard 持仓卡片
```typescript
interface Position {
  symbol: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
}
```

### OrderList 订单列表
```typescript
interface Order {
  orderId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: string;
  status: string;
  quantity: number;
  price: number;
  filledQuantity: number;
  createdAt: string;
}
```

## Trading 页面 K线图

使用 lightweight-charts 库：

```typescript
// components/charts/KlineChart.tsx
interface KlineChartProps {
  symbol: string;
  interval: '1m' | '5m' | '15m' | '1h' | '4h' | '1d';
  trades?: TradeMarker[];  // 交易标记
  onIntervalChange: (interval: string) => void;
}

interface TradeMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'arrowUp' | 'arrowDown';
  text: string;
}
```

## API 接口

```typescript
// api/trading.ts
export const tradingApi = {
  // 持仓
  getPositions: () => apiClient.get('/users/me/positions'),
  
  // 订单
  getOrders: (params?: { status?: string; limit?: number }) =>
    apiClient.get('/users/me/orders', { params }),
  cancelOrder: (orderId: string) =>
    apiClient.post(`/api/v1/orders/${orderId}/cancel`),
  
  // 收益
  getProfit: (period?: string) =>
    apiClient.get('/users/me/profit', { params: { period } }),
  
  // 风控
  getRisk: () => apiClient.get('/users/me/risk'),
};

// api/market.ts
export const marketApi = {
  getKlines: (symbol: string, interval: string, limit?: number) =>
    apiClient.get('/api/v1/data/klines', {
      params: { symbol, interval, limit },
    }),
};
```

## 状态管理

```typescript
// stores/tradingStore.ts
interface TradingState {
  positions: Position[];
  orders: Order[];
  balance: number;
  todayPnl: number;
  
  // WebSocket 更新
  updatePosition: (position: Position) => void;
  updateOrder: (order: Order) => void;
  removeOrder: (orderId: string) => void;
}

// stores/systemStore.ts
interface SystemState {
  currentState: string;
  currentRegime: string | null;
  isTradingAllowed: boolean;
  riskLevel: string;
  
  updateState: (state: Partial<SystemState>) => void;
}
```

## 数据流

```
WebSocket 连接
    │
    ├─ trading 频道
    │   ├─ position → tradingStore.updatePosition()
    │   └─ order → tradingStore.updateOrder()
    │
    ├─ risk 频道
    │   └─ metrics → riskStore.updateMetrics()
    │
    └─ state 频道
        └─ state_change → systemStore.updateState()
```
