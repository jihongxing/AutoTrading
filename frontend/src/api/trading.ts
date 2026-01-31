import apiClient from './client';
import type { ApiResponse } from './types';

export interface Position {
  symbol: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  leverage: number;
  liquidationPrice?: number;
}

export interface Order {
  orderId: string;
  clientOrderId?: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  orderType: string;
  status: string;
  quantity: number;
  filledQuantity: number;
  price?: number;
  avgPrice?: number;
  createdAt: string;
  updatedAt?: string;
}

export interface PositionListResponse {
  positions: Position[];
  totalUnrealizedPnl: number;
}

export interface OrderListResponse {
  orders: Order[];
  total: number;
}

export interface ProfitData {
  date: string;
  pnl: number;
  balance: number;
}

export const tradingApi = {
  getPositions: async (): Promise<PositionListResponse> => {
    try {
      const res = await apiClient.get<ApiResponse<{ positions: any[] }>>('/users/me/positions');
      if (!res.data.success) {
        throw new Error('NO_EXCHANGE');
      }
      const positions = res.data.data?.positions || [];
      return { 
        positions: positions.map((p: any) => ({
          symbol: p.symbol,
          side: p.side,
          quantity: parseFloat(p.positionAmt || p.quantity || 0),
          entryPrice: parseFloat(p.entryPrice || 0),
          currentPrice: parseFloat(p.markPrice || p.currentPrice || 0),
          unrealizedPnl: parseFloat(p.unRealizedProfit || p.unrealizedPnl || 0),
          unrealizedPnlPct: 0,
          leverage: parseInt(p.leverage || 1),
          liquidationPrice: p.liquidationPrice ? parseFloat(p.liquidationPrice) : undefined,
        })),
        totalUnrealizedPnl: positions.reduce((sum: number, p: any) => sum + parseFloat(p.unRealizedProfit || 0), 0),
      };
    } catch (err: any) {
      // 400 错误（NO_EXCHANGE）不应触发登出
      if (err.response?.status === 400 || err.response?.data?.detail?.code === 'NO_EXCHANGE') {
        throw new Error('NO_EXCHANGE');
      }
      // 其他错误返回空数据，避免触发登出
      console.warn('获取持仓失败:', err);
      return { positions: [], totalUnrealizedPnl: 0 };
    }
  },

  getOrders: async (params?: { status?: string; limit?: number }): Promise<OrderListResponse> => {
    try {
      const res = await apiClient.get<ApiResponse<{ orders: any[] }>>('/users/me/orders', { params });
      if (!res.data.success) {
        return { orders: [], total: 0 };
      }
      return { orders: res.data.data?.orders || [], total: res.data.data?.orders?.length || 0 };
    } catch (err: any) {
      // 400/NO_EXCHANGE 返回空数据
      console.warn('获取订单失败:', err);
      return { orders: [], total: 0 };
    }
  },

  cancelOrder: async (orderId: string): Promise<Order> => {
    const res = await apiClient.post<ApiResponse<Order>>(`/api/v1/orders/${orderId}/cancel`);
    if (!res.data.success || !res.data.data) throw new Error('撤销订单失败');
    return res.data.data;
  },

  getProfit: async (_period?: string): Promise<ProfitData[]> => {
    // TODO: 后端暂无此接口，返回空数组
    return [];
  },

  getRisk: async (): Promise<RiskStatus> => {
    try {
      const res = await apiClient.get<ApiResponse<{ risk_state: any }>>('/users/me/risk');
      if (!res.data.success || !res.data.data?.risk_state) {
        return {
          level: 'NORMAL',
          isLocked: false,
          dailyLoss: 0,
          currentDrawdown: 0,
          consecutiveLosses: 0,
        };
      }
      const r = res.data.data.risk_state;
      return {
        level: r.level || 'NORMAL',
        isLocked: r.is_locked || false,
        lockReason: r.lock_reason,
        dailyLoss: r.daily_loss || 0,
        currentDrawdown: r.current_drawdown || 0,
        consecutiveLosses: r.consecutive_losses || 0,
      };
    } catch {
      return {
        level: 'NORMAL',
        isLocked: false,
        dailyLoss: 0,
        currentDrawdown: 0,
        consecutiveLosses: 0,
      };
    }
  },
};

export interface RiskStatus {
  level: string;
  isLocked: boolean;
  lockReason?: string;
  dailyLoss: number;
  currentDrawdown: number;
  consecutiveLosses: number;
}
