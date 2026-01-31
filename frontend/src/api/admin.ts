import apiClient from './client';
import type { ApiResponse } from './types';

export interface PlatformStats {
  totalUsers: number;
  activeUsers: number;
  totalTrades: number;
  platformRevenue: number;
}

export interface AdminUser {
  userId: string;
  email: string;
  status: 'pending' | 'active' | 'suspended' | 'banned';
  subscription: string;
  createdAt: string;
  lastLoginAt?: string;
}

export interface AdminUsersResponse {
  users: AdminUser[];
  total: number;
  page: number;
  pageSize: number;
}

export interface UserDetail extends AdminUser {
  tradeCount: number;
  totalPnl: number;
  riskLevel: string;
  isLocked: boolean;
}

// 后端返回格式
interface BackendUser {
  user_id: string;
  email: string;
  status: string;
  subscription: string;
  created_at: string;
  updated_at: string;
  is_admin?: boolean;
}

interface BackendStats {
  users: { total: number; active: number; pending: number; suspended: number; banned: number };
  tradeable_users: number;
}

const transformUser = (u: BackendUser): AdminUser => ({
  userId: u.user_id,
  email: u.email,
  status: u.status as AdminUser['status'],
  subscription: u.subscription,
  createdAt: u.created_at,
});

export const adminApi = {
  getStats: async (): Promise<PlatformStats> => {
    const res = await apiClient.get<ApiResponse<BackendStats>>('/admin/stats');
    if (!res.data.success || !res.data.data) throw new Error('获取平台统计失败');
    const data = res.data.data;
    return {
      totalUsers: data.users?.total ?? 0,
      activeUsers: data.users?.active ?? 0,
      totalTrades: 0,
      platformRevenue: 0,
    };
  },

  getUsers: async (params?: {
    search?: string;
    status?: string;
    page?: number;
    pageSize?: number;
  }): Promise<AdminUsersResponse> => {
    const res = await apiClient.get<ApiResponse<{ users: BackendUser[]; total: number }>>('/admin/users', { params });
    if (!res.data.success || !res.data.data) throw new Error('获取用户列表失败');
    return {
      users: res.data.data.users.map(transformUser),
      total: res.data.data.total,
      page: params?.page ?? 1,
      pageSize: params?.pageSize ?? 10,
    };
  },

  getUser: async (id: string): Promise<UserDetail> => {
    const res = await apiClient.get<ApiResponse<{ user: BackendUser }>>(`/admin/users/${id}`);
    if (!res.data.success || !res.data.data) throw new Error('获取用户详情失败');
    const u = res.data.data.user;
    return {
      ...transformUser(u),
      tradeCount: 0,
      totalPnl: 0,
      riskLevel: 'normal',
      isLocked: false,
    };
  },

  suspendUser: async (id: string, reason: string): Promise<AdminUser> => {
    const res = await apiClient.post<ApiResponse<AdminUser>>(`/admin/users/${id}/suspend`, { reason });
    if (!res.data.success || !res.data.data) throw new Error('暂停用户失败');
    return res.data.data;
  },

  activateUser: async (id: string): Promise<AdminUser> => {
    const res = await apiClient.post<ApiResponse<AdminUser>>(`/admin/users/${id}/activate`);
    if (!res.data.success || !res.data.data) throw new Error('激活用户失败');
    return res.data.data;
  },

  forceLock: async (reason: string): Promise<void> => {
    const res = await apiClient.post<ApiResponse<void>>('/api/v1/state/force-lock', { reason });
    if (!res.data.success) throw new Error('强制锁定失败');
  },

  forceUnlock: async (): Promise<void> => {
    const res = await apiClient.post<ApiResponse<void>>('/api/v1/state/force-unlock');
    if (!res.data.success) throw new Error('解除锁定失败');
  },
};
