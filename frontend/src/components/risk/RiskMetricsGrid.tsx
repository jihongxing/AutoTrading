import { useTranslation } from 'react-i18next';
import { RiskGauge } from './RiskGauge';
import type { RiskStatus } from '@/api/risk';

interface RiskMetricsGridProps {
  status: RiskStatus | null;
  loading?: boolean;
}

export function RiskMetricsGrid({ status, loading }: RiskMetricsGridProps) {
  const { t } = useTranslation();

  if (loading || !status) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <RiskGauge
        label={t('risk.currentDrawdown')}
        current={status.currentDrawdown}
        threshold={status.maxDrawdown}
        unit="%"
        warningAt={0.5}
      />
      <RiskGauge
        label={t('risk.dailyLoss')}
        current={status.dailyLoss}
        threshold={status.maxDailyLoss}
        unit="%"
        warningAt={0.5}
      />
      <RiskGauge
        label={t('risk.consecutiveLosses')}
        current={status.consecutiveLosses}
        threshold={status.maxConsecutiveLosses}
        unit={t('risk.times')}
        warningAt={0.33}
      />
    </div>
  );
}
