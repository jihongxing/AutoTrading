import apiClient from './client';
import type { ApiResponse } from './types';

export interface Kline {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface KlineResponse {
  symbol: string;
  interval: string;
  bars: Kline[];
}

export const marketApi = {
  getKlines: async (symbol: string, interval: string, _limit = 100): Promise<KlineResponse> => {
    try {
      const res = await apiClient.get<ApiResponse<KlineResponse>>('/api/v1/market/bars', {
        params: { symbol, interval },
      });
      if (!res.data.success || !res.data.data) {
        return { symbol, interval, bars: [] };
      }
      return res.data.data;
    } catch {
      // 后端暂无此接口，返回空数据
      return { symbol, interval, bars: [] };
    }
  },
};
