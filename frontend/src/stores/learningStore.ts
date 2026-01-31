import { create } from 'zustand';
import type { LearningReport, Suggestion, WitnessRank } from '@/api/learning';

interface LearningStoreState {
  report: LearningReport | null;
  suggestions: Suggestion[];
  witnessRanking: WitnessRank[];
  isLoading: boolean;
  error: string | null;

  setReport: (report: LearningReport) => void;
  setSuggestions: (suggestions: Suggestion[]) => void;
  updateSuggestion: (id: string, status: Suggestion['status']) => void;
  setWitnessRanking: (ranking: WitnessRank[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useLearningStore = create<LearningStoreState>((set) => ({
  report: null,
  suggestions: [],
  witnessRanking: [],
  isLoading: false,
  error: null,

  setReport: (report) => set({ report }),

  setSuggestions: (suggestions) => set({ suggestions }),

  updateSuggestion: (id, status) =>
    set((s) => ({
      suggestions: s.suggestions.map((sug) =>
        sug.suggestionId === id ? { ...sug, status } : sug
      ),
    })),

  setWitnessRanking: (witnessRanking) => set({ witnessRanking }),

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
