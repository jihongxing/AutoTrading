import apiClient from './client';
import type { ApiResponse } from './types';

export interface SystemState {
  currentState: string;
  currentRegime: string | null;
  isTradingAllowed: boolean;
  riskLevel: string;
  uptime: number;
  lastHeartbeat: string;
}

export interface AccountInfo {
  balance: number;
  availableBalance: number;
  totalPnl: number;
  todayPnl: number;
  todayPnlPct: number;
}

// 后端返回格式（snake_case）
interface BackendStateResponse {
  current_state: string;
  current_regime: string | null;
  is_trading_allowed: boolean;
  risk_level: string;
  state_since?: string;
}

export const systemApi = {
  getState: async (): Promise<SystemState> => {
    const res = await apiClient.get<ApiResponse<BackendStateResponse>>('/api/v1/state');
    if (!res.data.success || !res.data.data) throw new Error('获取系统状态失败');
    const d = res.data.data;
    // 后端返回小写，前端显示大写
    const riskLevelMap: Record<string, string> = {
      'normal': 'LOW',
      'warning': 'MEDIUM',
      'cooldown': 'HIGH',
      'risk_locked': 'CRITICAL',
    };
    return {
      currentState: d.current_state.toUpperCase(),
      currentRegime: d.current_regime,
      isTradingAllowed: d.is_trading_allowed,
      riskLevel: riskLevelMap[d.risk_level] || d.risk_level.toUpperCase(),
      uptime: 0,
      lastHeartbeat: new Date().toISOString(),
    };
  },

  getAccount: async (): Promise<AccountInfo> => {
    try {
      const res = await apiClient.get<ApiResponse<{ balance: number }>>('/users/me/balance');
      if (!res.data.success || !res.data.data) throw new Error('获取账户信息失败');
      const balance = res.data.data.balance || 0;
      return {
        balance,
        availableBalance: balance,
        totalPnl: 0,
        todayPnl: 0,
        todayPnlPct: 0,
      };
    } catch {
      // 返回默认值
      return {
        balance: 0,
        availableBalance: 0,
        totalPnl: 0,
        todayPnl: 0,
        todayPnlPct: 0,
      };
    }
  },
};
