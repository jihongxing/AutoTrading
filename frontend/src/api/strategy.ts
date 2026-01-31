import apiClient from './client';
import type { ApiResponse } from './types';

export interface SystemStateInfo {
  currentState: string;
  currentRegime: string | null;
  isTradingAllowed: boolean;
  stateHistory: { state: string; timestamp: string }[];
}

export interface WitnessHealth {
  winRate: number;
  sampleCount: number;
  weight: number;
  grade: string;
}

export interface Witness {
  witnessId: string;
  name: string;
  tier: 'TIER1' | 'TIER2' | 'TIER3';
  status: 'ACTIVE' | 'MUTED' | 'PROBATION';
  isActive: boolean;
  health?: WitnessHealth;
  description?: string;
}

export interface Claim {
  claimId: string;
  witnessId: string;
  witnessName: string;
  direction: 'LONG' | 'SHORT';
  confidence: number;
  timestamp: string;
  status: 'PENDING' | 'ACCEPTED' | 'REJECTED';
  reason?: string;
}

export interface ClaimHistoryResponse {
  claims: Claim[];
  total: number;
}

// 后端返回的格式（snake_case）
interface BackendWitness {
  witness_id: string;
  tier: string;
  status: string;
  is_active: boolean;
  validity_window?: number;
  health?: {
    witness_id: string;
    tier: string;
    status: string;
    grade: string;
    win_rate: number;
    sample_count: number;
    weight: number;
  };
}

interface BackendStateInfo {
  current_state: string;
  current_regime: string | null;
  is_trading_allowed: boolean;
  state_since?: string;
  risk_level?: string;
}

// 转换函数
function toWitness(b: BackendWitness): Witness {
  // 后端返回 tier_1/tier_2/tier_3，前端期望 TIER1/TIER2/TIER3
  const tierMap: Record<string, Witness['tier']> = {
    'tier_1': 'TIER1',
    'tier_2': 'TIER2',
    'tier_3': 'TIER3',
  };
  const statusMap: Record<string, Witness['status']> = {
    'active': 'ACTIVE',
    'muted': 'MUTED',
    'probation': 'PROBATION',
  };
  
  return {
    witnessId: b.witness_id,
    name: b.witness_id,
    tier: tierMap[b.tier] || 'TIER2',
    status: statusMap[b.status] || 'ACTIVE',
    isActive: b.is_active,
    health: b.health ? {
      winRate: b.health.win_rate,
      sampleCount: b.health.sample_count,
      weight: b.health.weight,
      grade: b.health.grade,
    } : undefined,
  };
}

export const strategyApi = {
  getState: async (): Promise<SystemStateInfo> => {
    const res = await apiClient.get<ApiResponse<BackendStateInfo>>('/api/v1/state');
    if (!res.data.success || !res.data.data) throw new Error('获取状态失败');
    const d = res.data.data;
    return {
      currentState: d.current_state,
      currentRegime: d.current_regime,
      isTradingAllowed: d.is_trading_allowed,
      stateHistory: [],
    };
  },

  getWitnesses: async (): Promise<Witness[]> => {
    const res = await apiClient.get<ApiResponse<{ witnesses: BackendWitness[] }>>('/api/v1/witnesses');
    if (!res.data.success || !res.data.data) throw new Error('获取证人列表失败');
    return res.data.data.witnesses.map(toWitness);
  },

  getWitness: async (id: string): Promise<Witness> => {
    const res = await apiClient.get<ApiResponse<BackendWitness>>(`/api/v1/witnesses/${id}`);
    if (!res.data.success || !res.data.data) throw new Error('获取证人详情失败');
    return toWitness(res.data.data);
  },

  muteWitness: async (id: string): Promise<Witness> => {
    const res = await apiClient.post<ApiResponse<BackendWitness>>(`/api/v1/witnesses/${id}/mute`);
    if (!res.data.success || !res.data.data) throw new Error('静默证人失败');
    return toWitness(res.data.data);
  },

  activateWitness: async (id: string): Promise<Witness> => {
    const res = await apiClient.post<ApiResponse<BackendWitness>>(`/api/v1/witnesses/${id}/activate`);
    if (!res.data.success || !res.data.data) throw new Error('激活证人失败');
    return toWitness(res.data.data);
  },

  getClaims: async (_limit = 20): Promise<ClaimHistoryResponse> => {
    // 后端暂无此接口，返回空数据
    return { claims: [], total: 0 };
  },
};
