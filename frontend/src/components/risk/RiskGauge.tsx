import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';

interface RiskGaugeProps {
  label: string;
  current: number;
  threshold: number;
  unit?: string;
  warningAt?: number;
  className?: string;
}

export function RiskGauge({
  label,
  current,
  threshold,
  unit = '%',
  warningAt = 0.5,
  className,
}: RiskGaugeProps) {
  const { t } = useTranslation();
  const safeCurrentValue = current ?? 0;
  const safeThreshold = threshold ?? 1;
  const percent = Math.min((safeCurrentValue / safeThreshold) * 100, 100);
  const warningPercent = warningAt * 100;
  const dangerPercent = 80;

  const getColor = () => {
    if (percent >= dangerPercent) return 'text-red-500';
    if (percent >= warningPercent) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getBarColor = () => {
    if (percent >= dangerPercent) return 'bg-red-500';
    if (percent >= warningPercent) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className={cn('bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700', className)}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
        <span className={cn('text-lg font-bold', getColor())}>
          {safeCurrentValue.toFixed(1)}{unit}
        </span>
      </div>
      <div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={cn('absolute h-full rounded-full transition-all duration-300', getBarColor())}
          style={{ width: `${percent}%` }}
        />
        <div
          className="absolute h-full w-0.5 bg-gray-400 dark:bg-gray-500"
          style={{ left: `${warningPercent}%` }}
        />
        <div
          className="absolute h-full w-0.5 bg-red-400"
          style={{ left: `${dangerPercent}%` }}
        />
      </div>
      <div className="flex justify-between mt-1 text-xs text-gray-400">
        <span>0</span>
        <span>{t('risk.threshold')}: {safeThreshold}{unit}</span>
      </div>
    </div>
  );
}
