import { create } from 'zustand';
import type { RiskStatus, RiskEvent } from '@/api/risk';

interface RiskStoreState {
  status: RiskStatus | null;
  events: RiskEvent[];
  isLoading: boolean;
  error: string | null;

  setStatus: (status: RiskStatus) => void;
  updateStatus: (partial: Partial<RiskStatus>) => void;
  setEvents: (events: RiskEvent[]) => void;
  addEvent: (event: RiskEvent) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useRiskStore = create<RiskStoreState>((set) => ({
  status: null,
  events: [],
  isLoading: false,
  error: null,

  setStatus: (status) => set({ status }),

  updateStatus: (partial) =>
    set((s) => ({
      status: s.status ? { ...s.status, ...partial } : null,
    })),

  setEvents: (events) => set({ events }),

  addEvent: (event) =>
    set((s) => ({
      events: [event, ...s.events].slice(0, 100),
    })),

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
