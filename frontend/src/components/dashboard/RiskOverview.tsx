import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { ProgressBar } from '@/components/charts';
import type { RiskStatus } from '@/api/trading';

interface RiskOverviewProps {
  risk: RiskStatus | null;
  loading?: boolean;
  className?: string;
}

export function RiskOverview({ risk, loading, className }: RiskOverviewProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (!risk) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('dashboard.noRiskData')}
      </div>
    );
  }

  const getLevelColor = (level: string) => {
    const colors: Record<string, string> = {
      LOW: 'text-green-500',
      MEDIUM: 'text-yellow-500',
      HIGH: 'text-orange-500',
      CRITICAL: 'text-red-500',
    };
    return colors[level] || 'text-gray-500';
  };

  const getDrawdownVariant = (value: number): 'success' | 'warning' | 'danger' => {
    if (value < 10) return 'success';
    if (value < 15) return 'warning';
    return 'danger';
  };

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('risk.riskLevel')}</span>
        <span className={cn('font-semibold', getLevelColor(risk.level))}>
          {risk.level}
        </span>
      </div>

      {risk.isLocked && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-2">
            <span className="text-red-500">🔒</span>
            <span className="text-sm text-red-700 dark:text-red-400">
              {t('dashboard.tradingLocked')}: {risk.lockReason || t('dashboard.riskTriggered')}
            </span>
          </div>
        </div>
      )}

      <ProgressBar
        label={t('risk.currentDrawdown')}
        value={risk.currentDrawdown}
        max={20}
        variant={getDrawdownVariant(risk.currentDrawdown)}
      />

      <ProgressBar
        label={t('risk.dailyLoss')}
        value={risk.dailyLoss}
        max={3}
        variant={risk.dailyLoss > 2 ? 'danger' : risk.dailyLoss > 1 ? 'warning' : 'success'}
      />

      <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('dashboard.consecutiveLosses')}</span>
        <span
          className={cn(
            'font-medium',
            risk.consecutiveLosses >= 3 ? 'text-red-500' : 'text-gray-900 dark:text-white'
          )}
        >
          {risk.consecutiveLosses} {t('dashboard.times')}
        </span>
      </div>
    </div>
  );
}
