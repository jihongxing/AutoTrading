import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token 存储（内存中）
let accessToken: string | null = null;
let refreshToken: string | null = null;

export const setTokens = (access: string, refresh: string) => {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem('refreshToken', refresh);
};

export const getAccessToken = () => accessToken;

export const clearTokens = () => {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem('refreshToken');
};

export const loadRefreshToken = () => {
  refreshToken = localStorage.getItem('refreshToken');
  return refreshToken;
};

// 请求拦截器 - 添加 Authorization Header
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 刷新 Token - 全局单例 Promise
let refreshPromise: Promise<{ accessToken: string; refreshToken: string } | null> | null = null;

export const refreshAccessToken = async (token: string): Promise<{ accessToken: string; refreshToken: string } | null> => {
  // 如果已经在刷新，返回现有的 promise
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await axios.post<ApiResponse<{ tokens: { access_token: string; refresh_token: string } }>>(
        `${API_URL}/auth/refresh`,
        { refresh_token: token }
      );
      
      if (response.data.success && response.data.data) {
        const newAccessToken = response.data.data.tokens.access_token;
        const newRefreshToken = response.data.data.tokens.refresh_token;
        accessToken = newAccessToken;
        refreshToken = newRefreshToken;
        localStorage.setItem('refreshToken', newRefreshToken);
        return { accessToken: newAccessToken, refreshToken: newRefreshToken };
      }
      return null;
    } catch {
      clearTokens();
      return null;
    }
  })();
  
  const result = await refreshPromise;
  // 延迟清空，避免极短时间内的并发请求
  setTimeout(() => {
    refreshPromise = null;
  }, 500);
  return result;
};

// 响应拦截器 - 处理 401
let isRefreshing = false;
let refreshSubscribers: ((token: string | null) => void)[] = [];

const subscribeTokenRefresh = (cb: (token: string | null) => void) => {
  refreshSubscribers.push(cb);
};

const onTokenRefreshed = (token: string | null) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse<unknown>>) => {
    const originalRequest = error.config;
    
    // 400/500 错误不触发 token 刷新
    if (error.response?.status === 400 || error.response?.status === 500) {
      return Promise.reject(error);
    }
    
    if (error.response?.status === 401 && originalRequest) {
      // 如果是 refresh 请求本身失败，不要循环
      if (originalRequest.url?.includes('/auth/refresh')) {
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(error);
      }
      
      if (isRefreshing) {
        // 等待 Token 刷新完成
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((token: string | null) => {
            if (token && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(apiClient(originalRequest));
            } else {
              reject(error);
            }
          });
        });
      }

      isRefreshing = true;
      
      try {
        const storedRefreshToken = refreshToken || loadRefreshToken();
        if (!storedRefreshToken) {
          onTokenRefreshed(null);
          window.location.href = '/login';
          return Promise.reject(error);
        }
        
        const result = await refreshAccessToken(storedRefreshToken);
        
        if (result) {
          onTokenRefreshed(result.accessToken);
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${result.accessToken}`;
          }
          return apiClient(originalRequest);
        }
        
        // 刷新失败，跳转登录
        onTokenRefreshed(null);
        window.location.href = '/login';
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
