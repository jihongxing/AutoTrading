import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, Input, Select, Pagination, ConfirmDialog, toast } from '@/components/ui';
import { PlatformStats, UserTable, UserDetail, SystemActions, CoordinatorPanel } from '@/components/admin';
import { adminApi, type PlatformStats as PlatformStatsType, type AdminUser, type UserDetail as UserDetailType } from '@/api/admin';

export function AdminPage() {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<PlatformStatsType | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedUser, setSelectedUser] = useState<UserDetailType | null>(null);
  const [showUserDetail, setShowUserDetail] = useState(false);
  const [suspendUser, setSuspendUser] = useState<AdminUser | null>(null);
  const [suspendReason, setSuspendReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const pageSize = 10;
  const totalPages = Math.ceil(totalUsers / pageSize);

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await adminApi.getUsers({ search: search || undefined, status: statusFilter || undefined, page, pageSize });
      setUsers(res.users);
      setTotalUsers(res.total);
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter, page]);

  useEffect(() => {
    async function loadStats() {
      try {
        const statsRes = await adminApi.getStats();
        setStats(statsRes);
      } catch {}
    }
    loadStats();
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleViewDetail = async (user: AdminUser) => {
    try {
      const detail = await adminApi.getUser(user.userId);
      setSelectedUser(detail);
      setShowUserDetail(true);
    } catch {
      toast.error(t('common.failed'));
    }
  };

  const handleSuspendClick = (user: AdminUser) => { setSuspendUser(user); setSuspendReason(''); };

  const handleSuspendConfirm = async () => {
    if (!suspendUser || !suspendReason.trim()) return;
    setActionLoading(true);
    try {
      await adminApi.suspendUser(suspendUser.userId, suspendReason);
      toast.success(t('common.success'));
      setSuspendUser(null);
      loadUsers();
    } finally {
      setActionLoading(false);
    }
  };

  const handleActivate = async (user: AdminUser) => {
    setActionLoading(true);
    try {
      await adminApi.activateUser(user.userId);
      toast.success(t('common.success'));
      loadUsers();
    } finally {
      setActionLoading(false);
    }
  };

  const handleForceLock = async (reason: string) => { await adminApi.forceLock(reason); toast.success(t('common.success')); };
  const handleForceUnlock = async () => { await adminApi.forceUnlock(); toast.success(t('common.success')); };

  const statusOptions = [
    { value: '', label: t('common.noData') },
    { value: 'active', label: t('admin.activeUsers') },
    { value: 'suspended', label: t('admin.disable') },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('admin.title')}</h1>
      <PlatformStats stats={stats} loading={!stats} />
      <CoordinatorPanel />
      <Card>
        <CardHeader><CardTitle>{t('admin.userManagement')}</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-4">
            <Input placeholder={t('admin.email')} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="max-w-xs" />
            <Select value={statusFilter} onChange={(v) => { setStatusFilter(v); setPage(1); }} options={statusOptions} className="w-32" />
          </div>
          <UserTable users={users} loading={isLoading} onViewDetail={handleViewDetail} onSuspend={handleSuspendClick} onActivate={handleActivate} />
          {totalPages > 1 && <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-4" />}
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6"><SystemActions onForceLock={handleForceLock} onForceUnlock={handleForceUnlock} /></CardContent>
      </Card>
      <UserDetail user={selectedUser} isOpen={showUserDetail} onClose={() => setShowUserDetail(false)} onSuspend={() => selectedUser && handleSuspendClick(selectedUser as any)} onActivate={() => selectedUser && handleActivate(selectedUser as any)} loading={actionLoading} />
      <ConfirmDialog isOpen={!!suspendUser} onClose={() => setSuspendUser(null)} onConfirm={handleSuspendConfirm} title={t('admin.disable')} message="" confirmText={t('admin.disable')} variant="warning" loading={actionLoading}>
        <div className="mb-4">
          <p className="text-gray-600 dark:text-gray-300 mb-3">{suspendUser?.email}</p>
          <Input placeholder={t('learning.reason')} value={suspendReason} onChange={(e) => setSuspendReason(e.target.value)} />
        </div>
      </ConfirmDialog>
    </div>
  );
}
