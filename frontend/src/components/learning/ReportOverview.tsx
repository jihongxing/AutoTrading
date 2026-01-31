import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import type { LearningReport } from '@/api/learning';

interface ReportOverviewProps {
  report: LearningReport | null;
  loading?: boolean;
  className?: string;
}

export function ReportOverview({ report, loading, className }: ReportOverviewProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('grid grid-cols-2 md:grid-cols-4 gap-4', className)}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-20 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (!report) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('learning.noReport')}
      </div>
    );
  }

  const metrics = [
    { label: t('learning.totalTrades'), value: report.totalTrades.toString() },
    { label: t('learning.winRate'), value: `${(report.winRate * 100).toFixed(1)}%`, color: report.winRate >= 0.5 ? 'text-green-500' : 'text-red-500' },
    { label: t('learning.profitFactor'), value: report.profitFactor.toFixed(2), color: report.profitFactor >= 1 ? 'text-green-500' : 'text-red-500' },
    { label: t('learning.sharpeRatio'), value: report.sharpeRatio.toFixed(2), color: report.sharpeRatio >= 1 ? 'text-green-500' : 'text-yellow-500' },
    { label: t('learning.maxDrawdown'), value: `${report.maxDrawdown.toFixed(1)}%`, color: 'text-red-500' },
    { label: t('learning.avgHoldTime'), value: `${report.avgHoldTime.toFixed(1)}h` },
    { label: t('learning.bestWitness'), value: report.bestWitness, color: 'text-green-500' },
    { label: t('learning.worstWitness'), value: report.worstWitness, color: 'text-red-500' },
  ];

  return (
    <div className={cn('grid grid-cols-2 md:grid-cols-4 gap-4', className)}>
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <span className="text-sm text-gray-500 dark:text-gray-400">{metric.label}</span>
          <p className={cn('text-xl font-bold mt-1', metric.color || 'text-gray-900 dark:text-white')}>
            {metric.value}
          </p>
        </div>
      ))}
    </div>
  );
}
