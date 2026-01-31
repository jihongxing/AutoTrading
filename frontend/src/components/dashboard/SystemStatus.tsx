import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { getStatusColor } from '@/utils/format';
import type { SystemState } from '@/api/system';

interface SystemStatusProps {
  state: SystemState | null;
  wsConnected: boolean;
  loading?: boolean;
  className?: string;
}

export function SystemStatus({ state, wsConnected, loading, className }: SystemStatusProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-3', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  const getStateIcon = (stateName: string) => {
    const icons: Record<string, string> = {
      IDLE: '⚪',
      OBSERVING: '🔵',
      CLAIMING: '🟡',
      POSITIONED: '🟢',
      COOLDOWN: '🟠',
      LOCKED: '🔴',
    };
    return icons[stateName] || '⚪';
  };

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('dashboard.systemState')}</span>
        <div className="flex items-center gap-2">
          <span>{state ? getStateIcon(state.currentState) : '⚪'}</span>
          <span className={cn('font-medium', state ? getStatusColor(state.currentState) : '')}>
            {state?.currentState || 'UNKNOWN'}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('dashboard.marketState')}</span>
        <span className="text-sm text-gray-900 dark:text-white">
          {state?.currentRegime || '-'}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('dashboard.tradingAllowed')}</span>
        <span
          className={cn(
            'text-sm font-medium',
            state?.isTradingAllowed ? 'text-green-500' : 'text-red-500'
          )}
        >
          {state?.isTradingAllowed ? t('dashboard.allowed') : t('dashboard.forbidden')}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">WebSocket</span>
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              'w-2 h-2 rounded-full',
              wsConnected ? 'bg-green-500' : 'bg-red-500'
            )}
          />
          <span className="text-sm text-gray-900 dark:text-white">
            {wsConnected ? t('dashboard.connected') : t('dashboard.disconnected')}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('risk.riskLevel')}</span>
        <RiskLevelBadge level={state?.riskLevel || 'UNKNOWN'} />
      </div>
    </div>
  );
}

function RiskLevelBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    LOW: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    MEDIUM: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    HIGH: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    UNKNOWN: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400',
  };

  return (
    <span className={cn('px-2 py-0.5 text-xs font-medium rounded', colors[level] || colors.UNKNOWN)}>
      {level}
    </span>
  );
}
