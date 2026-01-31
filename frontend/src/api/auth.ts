import apiClient from './client';
import type { ApiResponse, LoginRequest, LoginResponse, RegisterRequest, User } from './types';

// 后端返回 snake_case，转换为 camelCase
interface BackendTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface BackendUser {
  user_id: string;
  email: string;
  status: string;
  subscription: string;
  trial_ends_at?: string;
  created_at: string;
  updated_at: string;
  is_admin?: boolean;
}

interface BackendLoginResponse {
  user: BackendUser;
  tokens: BackendTokens;
}

const transformUser = (u: BackendUser): User => ({
  userId: u.user_id,
  email: u.email,
  status: u.status as User['status'],
  subscription: u.subscription as User['subscription'],
  trialEndsAt: u.trial_ends_at,
  createdAt: u.created_at,
  updatedAt: u.updated_at,
  isAdmin: u.is_admin,
});

const transformLoginResponse = (data: BackendLoginResponse): LoginResponse => ({
  user: transformUser(data.user),
  tokens: {
    accessToken: data.tokens.access_token,
    refreshToken: data.tokens.refresh_token,
    tokenType: data.tokens.token_type,
    expiresIn: data.tokens.expires_in,
  },
});

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<ApiResponse<BackendLoginResponse>>('/auth/login', data);
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error?.message || '登录失败');
    }
    return transformLoginResponse(response.data.data);
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<ApiResponse<{ user: BackendUser }>>('/auth/register', data);
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error?.message || '注册失败');
    }
    return transformUser(response.data.data.user);
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  refresh: async (token: string): Promise<{ accessToken: string; refreshToken: string }> => {
    // 使用 client.ts 的统一 refresh 逻辑，避免并发问题
    const { refreshAccessToken } = await import('./client');
    const result = await refreshAccessToken(token);
    if (!result) {
      throw new Error('刷新失败');
    }
    return result;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<ApiResponse<{ user: BackendUser }>>('/users/me');
    if (!response.data.success || !response.data.data?.user) {
      throw new Error(response.data.error?.message || '获取用户信息失败');
    }
    return transformUser(response.data.data.user);
  },
};
