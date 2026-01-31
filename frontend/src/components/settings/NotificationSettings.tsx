import { useTranslation } from 'react-i18next';
import { Switch } from '@/components/ui';
import type { NotificationSettings as NotificationSettingsType } from '@/api/user';

interface NotificationSettingsProps {
  settings: NotificationSettingsType | null;
  loading?: boolean;
  onChange: (settings: NotificationSettingsType) => void;
}

export function NotificationSettings({ settings, loading, onChange }: NotificationSettingsProps) {
  const { t } = useTranslation();

  if (loading || !settings) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  const items = [
    { key: 'tradeExecution', label: t('settings.tradeExecution'), desc: t('settings.tradeExecutionDesc') },
    { key: 'riskWarning', label: t('settings.riskWarning'), desc: t('settings.riskWarningDesc') },
    { key: 'dailyReport', label: t('settings.dailyReport'), desc: t('settings.dailyReportDesc') },
  ] as const;

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.key} className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{item.label}</p>
            <p className="text-xs text-gray-500">{item.desc}</p>
          </div>
          <Switch
            checked={settings[item.key]}
            onChange={(checked) => onChange({ ...settings, [item.key]: checked })}
          />
        </div>
      ))}
    </div>
  );
}
