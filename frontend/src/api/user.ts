import apiClient from './client';
import type { ApiResponse } from './types';

export interface UserProfile {
  userId: string;
  email: string;
  subscription: string;
  trialEndsAt?: string;
  createdAt: string;
  isAdmin: boolean;
}

export interface ExchangeConfig {
  exchange: string;
  apiKeyMasked: string;
  isValid: boolean;
  lastVerifiedAt?: string;
  testnet: boolean;
  leverage: number;
  maxPositionPct: number;
}

export interface ExchangeConfigFormData {
  apiKey: string;
  apiSecret: string;
  testnet: boolean;
  leverage: number;
  maxPositionPct: number;
}

export interface PasswordChangeData {
  currentPassword: string;
  newPassword: string;
}

export interface NotificationSettings {
  tradeExecution: boolean;
  riskWarning: boolean;
  dailyReport: boolean;
}

// 后端返回格式
interface BackendUser {
  user_id: string;
  email: string;
  subscription: string;
  trial_ends_at?: string;
  created_at: string;
  is_admin: boolean;
}

interface BackendExchangeConfig {
  exchange?: string;
  api_key_masked?: string;
  is_valid: boolean;
  last_verified_at?: string;
  testnet: boolean;
  leverage: number;
  max_position_pct?: number;
}

function toUserProfile(b: BackendUser): UserProfile {
  return {
    userId: b.user_id,
    email: b.email,
    subscription: b.subscription,
    trialEndsAt: b.trial_ends_at,
    createdAt: b.created_at,
    isAdmin: b.is_admin,
  };
}

function toExchangeConfig(b: BackendExchangeConfig): ExchangeConfig {
  return {
    exchange: b.exchange || 'binance',
    apiKeyMasked: b.api_key_masked || '',
    isValid: b.is_valid,
    lastVerifiedAt: b.last_verified_at,
    testnet: b.testnet,
    leverage: b.leverage,
    maxPositionPct: Math.round((b.max_position_pct || 0.05) * 100),
  };
}

export const userApi = {
  getMe: async (): Promise<UserProfile> => {
    const res = await apiClient.get<ApiResponse<{ user: BackendUser }>>('/users/me');
    if (!res.data.success || !res.data.data?.user) throw new Error('获取用户信息失败');
    return toUserProfile(res.data.data.user);
  },

  updateMe: async (data: Partial<UserProfile>): Promise<UserProfile> => {
    const res = await apiClient.put<ApiResponse<{ user: BackendUser }>>('/users/me', {
      email: data.email,
    });
    if (!res.data.success || !res.data.data?.user) throw new Error('更新用户信息失败');
    return toUserProfile(res.data.data.user);
  },

  changePassword: async (data: PasswordChangeData): Promise<void> => {
    const res = await apiClient.put<ApiResponse<unknown>>('/users/me/password', {
      old_password: data.currentPassword,
      new_password: data.newPassword,
    });
    if (!res.data.success) throw new Error('修改密码失败');
  },

  getExchange: async (): Promise<ExchangeConfig | null> => {
    try {
      const res = await apiClient.get<ApiResponse<{ config: BackendExchangeConfig | null }>>('/users/me/exchange');
      if (!res.data.success || !res.data.data?.config) return null;
      return toExchangeConfig(res.data.data.config);
    } catch {
      return null;
    }
  },

  updateExchange: async (data: ExchangeConfigFormData): Promise<ExchangeConfig> => {
    const res = await apiClient.put<ApiResponse<{ config: BackendExchangeConfig }>>('/users/me/exchange', {
      api_key: data.apiKey,
      api_secret: data.apiSecret,
      testnet: data.testnet,
      leverage: data.leverage,
      max_position_pct: data.maxPositionPct / 100,
    });
    if (!res.data.success || !res.data.data?.config) throw new Error('更新交易所配置失败');
    return toExchangeConfig(res.data.data.config);
  },

  verifyExchange: async (): Promise<{ isValid: boolean }> => {
    const res = await apiClient.post<ApiResponse<{ is_valid: boolean }>>('/users/me/exchange/verify');
    return { isValid: res.data.data?.is_valid ?? false };
  },

  deleteExchange: async (): Promise<void> => {
    const res = await apiClient.delete<ApiResponse<unknown>>('/users/me/exchange');
    if (!res.data.success) throw new Error('删除交易所配置失败');
  },

  getNotifications: async (): Promise<NotificationSettings> => {
    // 后端暂无此接口，返回默认值
    return {
      tradeExecution: true,
      riskWarning: true,
      dailyReport: false,
    };
  },

  updateNotifications: async (data: NotificationSettings): Promise<NotificationSettings> => {
    // 后端暂无此接口，直接返回
    return data;
  },
};
