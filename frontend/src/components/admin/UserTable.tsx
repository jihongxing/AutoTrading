import { Table, Badge, Button } from '@/components/ui';
import { formatDateTime } from '@/utils/format';
import type { AdminUser } from '@/api/admin';

interface UserTableProps {
  users: AdminUser[];
  loading?: boolean;
  onViewDetail: (user: AdminUser) => void;
  onSuspend: (user: AdminUser) => void;
  onActivate: (user: AdminUser) => void;
}

export function UserTable({ users, loading, onViewDetail, onSuspend, onActivate }: UserTableProps) {
  const getStatusBadge = (status: AdminUser['status']) => {
    const variants: Record<AdminUser['status'], 'success' | 'warning' | 'danger' | 'default'> = {
      active: 'success',
      pending: 'warning',
      suspended: 'danger',
      banned: 'default',
    };
    return <Badge variant={variants[status]}>{status}</Badge>;
  };

  const columns = [
    { key: 'userId', header: 'ID', className: 'w-24' },
    { key: 'email', header: '邮箱' },
    {
      key: 'status',
      header: '状态',
      render: (user: AdminUser) => getStatusBadge(user.status),
    },
    { key: 'subscription', header: '订阅' },
    {
      key: 'createdAt',
      header: '注册时间',
      render: (user: AdminUser) => formatDateTime(user.createdAt),
    },
    {
      key: 'actions',
      header: '操作',
      render: (user: AdminUser) => (
        <div className="flex gap-1">
          <Button size="sm" variant="ghost" onClick={() => onViewDetail(user)}>
            详情
          </Button>
          {user.status === 'active' && (
            <Button size="sm" variant="ghost" onClick={() => onSuspend(user)}>
              暂停
            </Button>
          )}
          {user.status === 'suspended' && (
            <Button size="sm" variant="ghost" onClick={() => onActivate(user)}>
              激活
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      data={users}
      keyExtractor={(user) => user.userId}
      loading={loading}
      emptyText="暂无用户"
    />
  );
}
