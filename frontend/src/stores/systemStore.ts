import { create } from 'zustand';
import type { SystemState, AccountInfo } from '@/api/system';

interface SystemStoreState {
  state: SystemState | null;
  account: AccountInfo | null;
  isLoading: boolean;
  error: string | null;

  setState: (state: SystemState) => void;
  setAccount: (account: AccountInfo) => void;
  updateState: (partial: Partial<SystemState>) => void;
  updateAccount: (partial: Partial<AccountInfo>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useSystemStore = create<SystemStoreState>((set) => ({
  state: null,
  account: null,
  isLoading: false,
  error: null,

  setState: (state) => set({ state }),
  setAccount: (account) => set({ account }),

  updateState: (partial) =>
    set((s) => ({
      state: s.state ? { ...s.state, ...partial } : null,
    })),

  updateAccount: (partial) =>
    set((s) => ({
      account: s.account ? { ...s.account, ...partial } : null,
    })),

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
