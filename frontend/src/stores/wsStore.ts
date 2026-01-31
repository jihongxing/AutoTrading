import { create } from 'zustand';

interface WSState {
  isConnected: boolean;
  lastMessage: unknown | null;
  error: string | null;
  
  setConnected: (connected: boolean) => void;
  setLastMessage: (msg: unknown) => void;
  setError: (error: string | null) => void;
}

export const useWSStore = create<WSState>((set) => ({
  isConnected: false,
  lastMessage: null,
  error: null,
  
  setConnected: (connected) => set({ isConnected: connected }),
  setLastMessage: (msg) => set({ lastMessage: msg }),
  setError: (error) => set({ error }),
}));
