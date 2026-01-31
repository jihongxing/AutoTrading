import apiClient from './client';
import type { ApiResponse } from './types';

export interface StepData {
  success: boolean;
  bar_count: number;
  latest_price: number;
  symbol: string;
  interval: string;
  duration_ms: number;
  error: string | null;
}

export interface WitnessResult {
  witness_id: string;
  witness_name: string;
  tier: string;
  has_claim: boolean;
  claim_type: string | null;
  direction: string | null;
  confidence: number;
  reason: string;
}

export interface StepWitnesses {
  total_witnesses: number;
  active_witnesses: number;
  claims_generated: number;
  witnesses: WitnessResult[];
  duration_ms: number;
  skipped?: boolean;
}

export interface StepAggregation {
  total_claims: number;
  has_veto: boolean;
  veto_witness: string | null;
  dominant_direction: string | null;
  total_confidence: number;
  is_tradeable: boolean;
  resolution: string | null;
  reason: string;
  duration_ms: number;
  skipped?: boolean;
}

export interface RiskCheck {
  name: string;
  passed: boolean;
  level: string;
  reason: string;
}

export interface StepRisk {
  passed: boolean;
  overall_level: string;
  checks: RiskCheck[];
  duration_ms: number;
  skipped?: boolean;
}

export interface StepState {
  current_state: string;
  can_trade: boolean;
  new_state: string | null;
  reason: string;
  duration_ms: number;
  skipped?: boolean;
}

export interface StepExecution {
  should_execute: boolean;
  executed: boolean;
  action: string;
  order_id: string | null;
  reason: string;
  duration_ms: number;
  skipped?: boolean;
}

export interface LoopResult {
  loop_id: number;
  timestamp: string;
  step_data: StepData;
  step_witnesses: StepWitnesses;
  step_aggregation: StepAggregation;
  step_risk: StepRisk;
  step_state: StepState;
  step_execution: StepExecution;
  final_action: string;
  final_reason: string;
  total_duration_ms: number;
}

export interface LoopHistoryResponse {
  history: LoopResult[];
  total: number;
}

export const thinkingApi = {
  getHistory: async (limit = 50): Promise<LoopHistoryResponse> => {
    const response = await apiClient.get<ApiResponse<LoopHistoryResponse>>(
      `/api/v1/coordinator/history?limit=${limit}`
    );
    return response.data.data!;
  },
};
