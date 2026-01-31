import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, toast } from '@/components/ui';
import { AccountInfo, ExchangeConfig, ExchangeForm, NotificationSettings, PasswordChangeModal } from '@/components/settings';
import { userApi, type UserProfile, type ExchangeConfig as ExchangeConfigType, type NotificationSettings as NotificationSettingsType } from '@/api/user';
import { useMediaQuery } from '@/hooks/useMediaQuery';

export function SettingsPage() {
  const { t } = useTranslation();
  const isMobile = useMediaQuery('(max-width: 1023px)');
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [exchangeConfig, setExchangeConfig] = useState<ExchangeConfigType | null>(null);
  const [notifications, setNotifications] = useState<NotificationSettingsType | null>(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showExchangeForm, setShowExchangeForm] = useState(false);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [userRes, exchangeRes, notifRes] = await Promise.allSettled([
          userApi.getMe(),
          userApi.getExchange(),
          userApi.getNotifications(),
        ]);
        if (userRes.status === 'fulfilled') setUser(userRes.value);
        if (exchangeRes.status === 'fulfilled') setExchangeConfig(exchangeRes.value);
        if (notifRes.status === 'fulfilled') setNotifications(notifRes.value);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const handleChangePassword = async (data: { currentPassword: string; newPassword: string }) => {
    await userApi.changePassword(data);
    toast.success(t('common.success'));
  };

  const handleUpdateExchange = async (data: Parameters<typeof userApi.updateExchange>[0]) => {
    const result = await userApi.updateExchange(data);
    setExchangeConfig(result);
    toast.success(t('common.success'));
  };

  const handleVerifyExchange = async () => {
    const result = await userApi.verifyExchange();
    if (result.isValid) {
      setExchangeConfig((prev) => prev ? { ...prev, isValid: true } : null);
      toast.success(t('common.success'));
    } else {
      toast.error(t('common.failed'));
    }
  };

  const handleDeleteExchange = async () => {
    await userApi.deleteExchange();
    setExchangeConfig(null);
    toast.success(t('common.success'));
  };

  const handleUpdateNotifications = async (settings: NotificationSettingsType) => {
    const result = await userApi.updateNotifications(settings);
    setNotifications(result);
  };

  if (isMobile) {
    return (
      <div className="space-y-4 pb-20">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t('settings.title')}</h1>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('settings.accountInfo')}</CardTitle></CardHeader>
          <CardContent><AccountInfo user={user} loading={isLoading} onChangePassword={() => setShowPasswordModal(true)} /></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('settings.exchangeConfig')}</CardTitle></CardHeader>
          <CardContent><ExchangeConfig config={exchangeConfig} loading={isLoading} onEdit={() => setShowExchangeForm(true)} onVerify={handleVerifyExchange} onDelete={handleDeleteExchange} /></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('settings.notifications')}</CardTitle></CardHeader>
          <CardContent><NotificationSettings settings={notifications} loading={isLoading} onChange={handleUpdateNotifications} /></CardContent>
        </Card>
        <PasswordChangeModal isOpen={showPasswordModal} onClose={() => setShowPasswordModal(false)} onSubmit={handleChangePassword} />
        <ExchangeForm isOpen={showExchangeForm} onClose={() => setShowExchangeForm(false)} onSubmit={handleUpdateExchange} initialData={exchangeConfig} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('settings.title')}</h1>
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>{t('settings.accountInfo')}</CardTitle></CardHeader>
          <CardContent><AccountInfo user={user} loading={isLoading} onChangePassword={() => setShowPasswordModal(true)} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>{t('settings.notifications')}</CardTitle></CardHeader>
          <CardContent><NotificationSettings settings={notifications} loading={isLoading} onChange={handleUpdateNotifications} /></CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader><CardTitle>{t('settings.exchangeConfig')}</CardTitle></CardHeader>
        <CardContent><ExchangeConfig config={exchangeConfig} loading={isLoading} onEdit={() => setShowExchangeForm(true)} onVerify={handleVerifyExchange} onDelete={handleDeleteExchange} /></CardContent>
      </Card>
      <PasswordChangeModal isOpen={showPasswordModal} onClose={() => setShowPasswordModal(false)} onSubmit={handleChangePassword} />
      <ExchangeForm isOpen={showExchangeForm} onClose={() => setShowExchangeForm(false)} onSubmit={handleUpdateExchange} initialData={exchangeConfig} />
    </div>
  );
}
