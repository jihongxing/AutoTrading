import { useAuthStore } from '@/stores/authStore';

export function usePermission() {
  const user = useAuthStore((s) => s.user);

  return {
    isAdmin: user?.isAdmin ?? false,
    canManageUsers: user?.isAdmin ?? false,
    canForceLock: user?.isAdmin ?? false,
  };
}
