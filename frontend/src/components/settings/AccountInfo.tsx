import { useTranslation } from 'react-i18next';
import { Button, Badge } from '@/components/ui';
import { formatDateTime } from '@/utils/format';
import type { UserProfile } from '@/api/user';

interface AccountInfoProps {
  user: UserProfile | null;
  loading?: boolean;
  onChangePassword: () => void;
}

export function AccountInfo({ user, loading, onChangePassword }: AccountInfoProps) {
  const { t } = useTranslation();

  if (loading || !user) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  const getSubscriptionBadge = (sub: string) => {
    switch (sub) {
      case 'PRO':
        return <Badge variant="success">PRO</Badge>;
      case 'TRIAL':
        return <Badge variant="warning">{t('settings.trial')}</Badge>;
      default:
        return <Badge variant="default">{t('settings.free')}</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.email')}</span>
        <span className="text-gray-900 dark:text-white">{user.email}</span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.subscription')}</span>
        <div className="flex items-center gap-2">
          {getSubscriptionBadge(user.subscription)}
          {user.trialEndsAt && (
            <span className="text-xs text-gray-500">
              {t('settings.expiresAt')}: {formatDateTime(user.trialEndsAt)}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.registeredAt')}</span>
        <span className="text-sm text-gray-900 dark:text-white">
          {formatDateTime(user.createdAt)}
        </span>
      </div>

      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button variant="outline" size="sm" onClick={onChangePassword}>
          {t('settings.changePassword')}
        </Button>
      </div>
    </div>
  );
}
