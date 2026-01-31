import { Modal, Badge, Button } from '@/components/ui';
import { formatDateTime, formatCurrency } from '@/utils/format';
import type { UserDetail as UserDetailType } from '@/api/admin';

interface UserDetailProps {
  user: UserDetailType | null;
  isOpen: boolean;
  onClose: () => void;
  onSuspend: () => void;
  onActivate: () => void;
  loading?: boolean;
}

export function UserDetail({ user, isOpen, onClose, onSuspend, onActivate, loading }: UserDetailProps) {
  if (!user) return null;

  const getStatusBadge = (status: UserDetailType['status']) => {
    const variants: Record<UserDetailType['status'], 'success' | 'warning' | 'danger' | 'default'> = {
      active: 'success',
      pending: 'warning',
      suspended: 'danger',
      banned: 'default',
    };
    return <Badge variant={variants[status]}>{status}</Badge>;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="用户详情" size="md">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-lg font-bold text-gray-900 dark:text-white">{user.email}</span>
          {getStatusBadge(user.status)}
        </div>

        <div className="grid grid-cols-2 gap-4 py-4 border-y border-gray-200 dark:border-gray-700">
          <div>
            <span className="text-sm text-gray-500">用户 ID</span>
            <p className="font-medium text-gray-900 dark:text-white">{user.userId}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">订阅</span>
            <p className="font-medium text-gray-900 dark:text-white">{user.subscription}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">注册时间</span>
            <p className="font-medium text-gray-900 dark:text-white">{formatDateTime(user.createdAt)}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">最后登录</span>
            <p className="font-medium text-gray-900 dark:text-white">
              {user.lastLoginAt ? formatDateTime(user.lastLoginAt) : '-'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm text-gray-500">交易次数</span>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{user.tradeCount}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">总盈亏</span>
            <p className={`text-lg font-bold ${user.totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatCurrency(user.totalPnl)}
            </p>
          </div>
          <div>
            <span className="text-sm text-gray-500">风险等级</span>
            <p className="font-medium text-gray-900 dark:text-white">{user.riskLevel}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">锁定状态</span>
            <p className="font-medium text-gray-900 dark:text-white">
              {user.isLocked ? '🔒 已锁定' : '🔓 正常'}
            </p>
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          {user.status === 'active' && (
            <Button variant="warning" onClick={onSuspend} loading={loading} className="flex-1">
              暂停用户
            </Button>
          )}
          {user.status === 'suspended' && (
            <Button variant="primary" onClick={onActivate} loading={loading} className="flex-1">
              激活用户
            </Button>
          )}
          <Button variant="ghost" onClick={onClose} className="flex-1">
            关闭
          </Button>
        </div>
      </div>
    </Modal>
  );
}
