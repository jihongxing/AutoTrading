import { create } from 'zustand';
import type { Position, Order, ProfitData } from '@/api/trading';

interface TradingState {
  positions: Position[];
  orders: Order[];
  profitHistory: ProfitData[];
  totalUnrealizedPnl: number;
  isLoading: boolean;
  error: string | null;

  setPositions: (positions: Position[], totalPnl?: number) => void;
  updatePosition: (position: Position) => void;
  removePosition: (symbol: string) => void;
  setOrders: (orders: Order[]) => void;
  updateOrder: (order: Order) => void;
  removeOrder: (orderId: string) => void;
  setProfitHistory: (data: ProfitData[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useTradingStore = create<TradingState>((set) => ({
  positions: [],
  orders: [],
  profitHistory: [],
  totalUnrealizedPnl: 0,
  isLoading: false,
  error: null,

  setPositions: (positions, totalPnl) =>
    set({ positions, totalUnrealizedPnl: totalPnl ?? 0 }),

  updatePosition: (position) =>
    set((state) => {
      const idx = state.positions.findIndex((p) => p.symbol === position.symbol);
      if (idx >= 0) {
        const newPositions = [...state.positions];
        newPositions[idx] = position;
        return { positions: newPositions };
      }
      return { positions: [...state.positions, position] };
    }),

  removePosition: (symbol) =>
    set((state) => ({
      positions: state.positions.filter((p) => p.symbol !== symbol),
    })),

  setOrders: (orders) => set({ orders }),

  updateOrder: (order) =>
    set((state) => {
      const idx = state.orders.findIndex((o) => o.orderId === order.orderId);
      if (idx >= 0) {
        const newOrders = [...state.orders];
        newOrders[idx] = order;
        return { orders: newOrders };
      }
      return { orders: [...state.orders, order] };
    }),

  removeOrder: (orderId) =>
    set((state) => ({
      orders: state.orders.filter((o) => o.orderId !== orderId),
    })),

  setProfitHistory: (data) => set({ profitHistory: data }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
