import apiClient from './client';
import type { ApiResponse } from './types';

export interface CoordinatorMetrics {
  total_loops: number;
  claims_generated: number;
  trades_executed: number;
  risk_rejections: number;
  errors: number;
  last_loop_time: number;
  last_error: string | null;
}

export interface CoordinatorStatus {
  is_running: boolean;
  trading_enabled: boolean;
  loop_interval: number;
  metrics: CoordinatorMetrics;
  system_state: string;
}

export const coordinatorApi = {
  getStatus: async (): Promise<CoordinatorStatus> => {
    const res = await apiClient.get<ApiResponse<CoordinatorStatus>>('/api/v1/coordinator/status');
    if (!res.data.success || !res.data.data) throw new Error('获取协调器状态失败');
    return res.data.data;
  },

  start: async (): Promise<void> => {
    const res = await apiClient.post<ApiResponse<{ message: string }>>('/api/v1/coordinator/start');
    if (!res.data.success) throw new Error('启动协调器失败');
  },

  stop: async (): Promise<void> => {
    const res = await apiClient.post<ApiResponse<{ message: string }>>('/api/v1/coordinator/stop');
    if (!res.data.success) throw new Error('停止协调器失败');
  },

  enableTrading: async (): Promise<void> => {
    const res = await apiClient.post<ApiResponse<{ message: string }>>('/api/v1/coordinator/enable-trading');
    if (!res.data.success) throw new Error('启用交易失败');
  },

  disableTrading: async (): Promise<void> => {
    const res = await apiClient.post<ApiResponse<{ message: string }>>('/api/v1/coordinator/disable-trading');
    if (!res.data.success) throw new Error('禁用交易失败');
  },
};
