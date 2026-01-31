import apiClient from './client';
import type { ApiResponse } from './types';

export interface StrategyLifecycle {
  strategyId: string;
  status: 'CANDIDATE' | 'SHADOW' | 'ACTIVE' | 'DEGRADED' | 'RETIRED';
  tier: string;
  healthGrade: string;
  effectiveWeight: number;
}

export interface ShadowPerformance {
  strategyId: string;
  totalTrades: number;
  winRate: number;
  totalPnl: number;
  sharpeRatio: number;
  maxDrawdown: number;
  startTime: string;
}

export interface StrategiesResponse {
  active: StrategyLifecycle[];
  degraded: StrategyLifecycle[];
  retired: StrategyLifecycle[];
  total: number;
}

export interface ShadowResponse {
  strategies: ShadowPerformance[];
  total: number;
}

// 后端返回格式
interface BackendStrategiesResponse {
  active: any[];
  degraded: any[];
  retired: any[];
  total: number;
}

interface BackendShadowResponse {
  strategies: any[];
  total: number;
}

export const lifecycleApi = {
  getStrategies: async (): Promise<StrategiesResponse> => {
    try {
      const res = await apiClient.get<ApiResponse<BackendStrategiesResponse>>('/api/v1/lifecycle/strategies');
      if (!res.data.success || !res.data.data) throw new Error('获取策略列表失败');
      const d = res.data.data;
      const mapStrategy = (s: any): StrategyLifecycle => ({
        strategyId: s.strategy_id || s.strategyId,
        status: s.status?.toUpperCase() || 'ACTIVE',
        tier: s.tier?.toUpperCase() || 'TIER2',
        healthGrade: s.health_grade || s.healthGrade || 'B',
        effectiveWeight: s.effective_weight || s.effectiveWeight || 0.5,
      });
      return {
        active: (d.active || []).map(mapStrategy),
        degraded: (d.degraded || []).map(mapStrategy),
        retired: (d.retired || []).map(mapStrategy),
        total: d.total || 0,
      };
    } catch {
      return { active: [], degraded: [], retired: [], total: 0 };
    }
  },

  getShadowStrategies: async (): Promise<ShadowResponse> => {
    try {
      const res = await apiClient.get<ApiResponse<BackendShadowResponse>>('/api/v1/lifecycle/shadow');
      if (!res.data.success || !res.data.data) throw new Error('获取影子策略失败');
      const d = res.data.data;
      return {
        strategies: (d.strategies || []).map((s: any) => ({
          strategyId: s.strategy_id || s.strategyId,
          totalTrades: s.total_trades || s.totalTrades || 0,
          winRate: s.win_rate || s.winRate || 0,
          totalPnl: s.total_pnl || s.totalPnl || 0,
          sharpeRatio: s.sharpe_ratio || s.sharpeRatio || 0,
          maxDrawdown: s.max_drawdown || s.maxDrawdown || 0,
          startTime: s.start_time || s.startTime || new Date().toISOString(),
        })),
        total: d.total || 0,
      };
    } catch {
      return { strategies: [], total: 0 };
    }
  },

  promoteStrategy: async (strategyId: string): Promise<boolean> => {
    const res = await apiClient.post<ApiResponse<{ promoted: boolean }>>(`/api/v1/lifecycle/strategies/${strategyId}/promote`, {
      by: 'user',
    });
    return res.data.success && res.data.data?.promoted === true;
  },

  demoteStrategy: async (strategyId: string, reason: string): Promise<boolean> => {
    const res = await apiClient.post<ApiResponse<{ demoted: boolean }>>(`/api/v1/lifecycle/strategies/${strategyId}/demote`, {
      by: 'user',
      reason,
    });
    return res.data.success && res.data.data?.demoted === true;
  },

  retireStrategy: async (strategyId: string): Promise<boolean> => {
    const res = await apiClient.post<ApiResponse<{ retired: boolean }>>(`/api/v1/lifecycle/strategies/${strategyId}/retire`, {
      by: 'user',
      reason: '手动退役',
    });
    return res.data.success && res.data.data?.retired === true;
  },
};
