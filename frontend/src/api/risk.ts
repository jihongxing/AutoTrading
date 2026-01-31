import apiClient from './client';
import type { ApiResponse } from './types';

export interface RiskStatus {
  level: string;
  isLocked: boolean;
  lockReason: string | null;
  currentDrawdown: number;
  dailyLoss: number;
  consecutiveLosses: number;
  maxDrawdown: number;
  maxDailyLoss: number;
  maxConsecutiveLosses: number;
}

export interface RiskEvent {
  eventId: string;
  timestamp: string;
  eventType: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  details?: Record<string, unknown>;
}

export interface RiskEventsResponse {
  events: RiskEvent[];
  total: number;
}

// 后端返回格式
interface BackendRiskStatus {
  level: string;
  is_locked: boolean;
  lock_reason: string | null;
  lock_since?: string;
  recent_events: any[];
  daily_loss: number;
  current_drawdown: number;
}

interface BackendRiskEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  severity: string;
  message: string;
  details?: Record<string, unknown>;
}

export const riskApi = {
  getStatus: async (): Promise<RiskStatus> => {
    try {
      const res = await apiClient.get<ApiResponse<BackendRiskStatus>>('/api/v1/risk/status');
      if (!res.data.success || !res.data.data) {
        return {
          level: 'NORMAL',
          isLocked: false,
          lockReason: null,
          currentDrawdown: 0,
          dailyLoss: 0,
          consecutiveLosses: 0,
          maxDrawdown: 20,
          maxDailyLoss: 3,
          maxConsecutiveLosses: 3,
        };
      }
      const d = res.data.data;
      return {
        level: d.level,
        isLocked: d.is_locked,
        lockReason: d.lock_reason,
        currentDrawdown: d.current_drawdown || 0,
        dailyLoss: d.daily_loss || 0,
        consecutiveLosses: 0,
        maxDrawdown: 20,
        maxDailyLoss: 3,
        maxConsecutiveLosses: 3,
      };
    } catch {
      return {
        level: 'NORMAL',
        isLocked: false,
        lockReason: null,
        currentDrawdown: 0,
        dailyLoss: 0,
        consecutiveLosses: 0,
        maxDrawdown: 20,
        maxDailyLoss: 3,
        maxConsecutiveLosses: 3,
      };
    }
  },

  getEvents: async (limit = 50): Promise<RiskEventsResponse> => {
    try {
      const res = await apiClient.get<ApiResponse<BackendRiskEvent[]>>('/api/v1/risk/events', {
        params: { limit },
      });
      if (!res.data.success || !res.data.data) {
        return { events: [], total: 0 };
      }
      const events = res.data.data.map((e) => ({
        eventId: e.event_id,
        timestamp: e.timestamp,
        eventType: e.event_type,
        severity: (e.severity === 'CRITICAL' ? 'critical' : e.severity === 'WARNING' ? 'warning' : 'info') as RiskEvent['severity'],
        message: e.message,
        details: e.details,
      }));
      return { events, total: events.length };
    } catch {
      return { events: [], total: 0 };
    }
  },
};
