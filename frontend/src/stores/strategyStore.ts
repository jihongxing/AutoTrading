import { create } from 'zustand';
import type { Witness, Claim, SystemStateInfo } from '@/api/strategy';

interface StrategyStoreState {
  stateInfo: SystemStateInfo | null;
  witnesses: Witness[];
  claims: Claim[];
  isLoading: boolean;
  error: string | null;

  setStateInfo: (info: SystemStateInfo) => void;
  updateState: (state: string) => void;
  setWitnesses: (witnesses: Witness[]) => void;
  updateWitness: (witness: Witness) => void;
  setClaims: (claims: Claim[]) => void;
  addClaim: (claim: Claim) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useStrategyStore = create<StrategyStoreState>((set) => ({
  stateInfo: null,
  witnesses: [],
  claims: [],
  isLoading: false,
  error: null,

  setStateInfo: (stateInfo) => set({ stateInfo }),

  updateState: (state) =>
    set((s) => ({
      stateInfo: s.stateInfo
        ? {
            ...s.stateInfo,
            currentState: state,
            stateHistory: [
              { state, timestamp: new Date().toISOString() },
              ...s.stateInfo.stateHistory,
            ].slice(0, 20),
          }
        : null,
    })),

  setWitnesses: (witnesses) => set({ witnesses }),

  updateWitness: (witness) =>
    set((s) => ({
      witnesses: s.witnesses.map((w) =>
        w.witnessId === witness.witnessId ? witness : w
      ),
    })),

  setClaims: (claims) => set({ claims }),

  addClaim: (claim) =>
    set((s) => ({
      claims: [claim, ...s.claims].slice(0, 50),
    })),

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
