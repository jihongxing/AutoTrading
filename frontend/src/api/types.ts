// API 响应类型

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  timestamp: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// 用户类型
export interface User {
  userId: string;
  email: string;
  status: UserStatus;
  subscription: SubscriptionPlan;
  trialEndsAt?: string;
  createdAt: string;
  updatedAt: string;
  isAdmin?: boolean;
}

export type UserStatus = 'pending' | 'active' | 'suspended' | 'banned';
export type SubscriptionPlan = 'free' | 'basic' | 'pro';

// 认证类型
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
}
