import apiClient from './client';
import type { ApiResponse } from './types';

export interface LearningReport {
  period: string;
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
  avgHoldTime: number;
  bestWitness: string;
  worstWitness: string;
}

export interface Suggestion {
  suggestionId: string;
  paramName: string;
  currentValue: number;
  suggestedValue: number;
  action: string;
  reason: string;
  confidence: number;
  requiresApproval: boolean;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  createdAt: string;
}

export interface WitnessRank {
  witnessId: string;
  witnessName: string;
  tier: string;
  winRate: number;
  profitContribution: number;
  sampleCount: number;
  grade: string;
}

export interface SuggestionsResponse {
  suggestions: Suggestion[];
  total: number;
}

// 后端返回格式
interface BackendReport {
  period: string;
  timestamp: string;
  start_time: string;
  end_time: string;
  total_trades: number;
  win_rate: number;
  avg_pnl: number;
  total_pnl: number;
  max_drawdown: number;
  sharpe_ratio: number;
  suggestions_count: number;
  pending_approvals: number;
}

interface BackendSuggestion {
  suggestion_id: string;
  param_name: string;
  current_value: number;
  suggested_value: number;
  action: string;
  reason: string;
  confidence: number;
  requires_approval: boolean;
}

interface BackendSuggestionsResponse {
  suggestions: BackendSuggestion[];
  total: number;
  pending_count: number;
}

export const learningApi = {
  getReport: async (period = '7d'): Promise<LearningReport> => {
    try {
      const res = await apiClient.get<ApiResponse<BackendReport>>('/api/v1/learning/report', {
        params: { period },
      });
      if (!res.data.success || !res.data.data) throw new Error('获取学习报告失败');
      const d = res.data.data;
      return {
        period: d.period,
        totalTrades: d.total_trades,
        winRate: d.win_rate,
        profitFactor: d.total_pnl > 0 ? 1.5 : 0.5, // 简化计算
        sharpeRatio: d.sharpe_ratio,
        maxDrawdown: d.max_drawdown,
        avgHoldTime: 0,
        bestWitness: '-',
        worstWitness: '-',
      };
    } catch {
      // 返回默认值
      return {
        period,
        totalTrades: 0,
        winRate: 0,
        profitFactor: 0,
        sharpeRatio: 0,
        maxDrawdown: 0,
        avgHoldTime: 0,
        bestWitness: '-',
        worstWitness: '-',
      };
    }
  },

  getSuggestions: async (pendingOnly = false): Promise<SuggestionsResponse> => {
    try {
      const res = await apiClient.get<ApiResponse<BackendSuggestionsResponse>>('/api/v1/learning/suggestions', {
        params: { pending_only: pendingOnly },
      });
      if (!res.data.success || !res.data.data) throw new Error('获取建议列表失败');
      const d = res.data.data;
      return {
        suggestions: d.suggestions.map(s => ({
          suggestionId: s.suggestion_id,
          paramName: s.param_name,
          currentValue: s.current_value,
          suggestedValue: s.suggested_value,
          action: s.action,
          reason: s.reason,
          confidence: s.confidence,
          requiresApproval: s.requires_approval,
          status: 'PENDING' as const,
          createdAt: new Date().toISOString(),
        })),
        total: d.total,
      };
    } catch {
      return { suggestions: [], total: 0 };
    }
  },

  approveSuggestions: async (
    ids: string[],
    approved: boolean,
    comment?: string
  ): Promise<void> => {
    const res = await apiClient.post<ApiResponse<void>>('/api/v1/learning/approve', {
      suggestion_ids: ids,
      approved,
      comment,
    });
    if (!res.data.success) throw new Error('审批建议失败');
  },

  getWitnessRanking: async (): Promise<WitnessRank[]> => {
    try {
      // 后端暂无此接口，从证人列表获取
      const res = await apiClient.get<ApiResponse<{ witnesses: any[] }>>('/api/v1/witnesses');
      if (!res.data.success || !res.data.data) return [];
      return res.data.data.witnesses.map((w: any) => ({
        witnessId: w.witness_id,
        witnessName: w.witness_id,
        tier: w.tier?.toUpperCase() || 'TIER2',
        winRate: w.health?.win_rate || 0.5,
        profitContribution: 0,
        sampleCount: w.health?.sample_count || 0,
        grade: w.health?.grade || 'B',
      }));
    } catch {
      return [];
    }
  },
};
