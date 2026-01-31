import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi } from '@/api/auth';
import { setTokens, clearTokens, loadRefreshToken } from '@/api/client';
import type { User } from '@/api/types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,  // 初始为 true，等待 checkAuth 完成
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login({ email, password });
          setTokens(response.tokens.accessToken, response.tokens.refreshToken);
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : '登录失败',
            isLoading: false,
          });
          throw err;
        }
      },

      register: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          await authApi.register({ email, password });
          set({ isLoading: false });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : '注册失败',
            isLoading: false,
          });
          throw err;
        }
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch {
          // 忽略登出错误
        } finally {
          clearTokens();
          set({ user: null, isAuthenticated: false });
        }
      },

      checkAuth: async () => {
        const storedRefreshToken = loadRefreshToken();
        if (!storedRefreshToken) {
          set({ isAuthenticated: false, user: null, isLoading: false });
          return;
        }

        set({ isLoading: true });
        try {
          // 使用 client.ts 的统一 refresh 逻辑
          const { authApi } = await import('@/api/auth');
          const refreshResult = await authApi.refresh(storedRefreshToken);
          
          if (refreshResult.accessToken) {
            // 刷新成功，设置新 token
            setTokens(refreshResult.accessToken, refreshResult.refreshToken);
            
            // 获取用户信息
            const user = await authApi.getMe();
            set({ user, isAuthenticated: true, isLoading: false });
          } else {
            clearTokens();
            set({ user: null, isAuthenticated: false, isLoading: false });
          }
        } catch {
          clearTokens();
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user }),
    }
  )
);
