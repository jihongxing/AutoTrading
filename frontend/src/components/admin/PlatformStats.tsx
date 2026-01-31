import { cn } from '@/utils/cn';
import { formatCurrency, formatNumber } from '@/utils/format';
import type { PlatformStats as PlatformStatsType } from '@/api/admin';

interface PlatformStatsProps {
  stats: PlatformStatsType | null;
  loading?: boolean;
  className?: string;
}

export function PlatformStats({ stats, loading, className }: PlatformStatsProps) {
  if (loading) {
    return (
      <div className={cn('grid grid-cols-4 gap-4', className)}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-20 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const items = [
    { label: '总用户数', value: formatNumber(stats.totalUsers, 0) },
    { label: '活跃用户', value: formatNumber(stats.activeUsers, 0) },
    { label: '总交易量', value: formatNumber(stats.totalTrades, 0) },
    { label: '平台收益', value: formatCurrency(stats.platformRevenue) },
  ];

  return (
    <div className={cn('grid grid-cols-4 gap-4', className)}>
      {items.map((item) => (
        <div
          key={item.label}
          className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <span className="text-sm text-gray-500 dark:text-gray-400">{item.label}</span>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
