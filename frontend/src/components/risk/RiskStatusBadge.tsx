import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';

interface RiskStatusBadgeProps {
  level: string;
  isLocked?: boolean;
  className?: string;
}

export function RiskStatusBadge({ level, isLocked, className }: RiskStatusBadgeProps) {
  const { t } = useTranslation();

  const getConfig = () => {
    if (isLocked) {
      return { icon: '🔒', text: t('risk.locked'), color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' };
    }
    switch (level) {
      case 'LOW':
        return { icon: '🟢', text: t('risk.low'), color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' };
      case 'MEDIUM':
        return { icon: '🟡', text: t('risk.medium'), color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' };
      case 'HIGH':
        return { icon: '🟠', text: t('risk.high'), color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' };
      case 'CRITICAL':
        return { icon: '🔴', text: t('risk.critical'), color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' };
      default:
        return { icon: '⚪', text: level, color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' };
    }
  };

  const config = getConfig();

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium',
        config.color,
        className
      )}
    >
      <span>{config.icon}</span>
      <span>{config.text}</span>
    </span>
  );
}
