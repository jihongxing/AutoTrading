import { cn } from '@/utils/cn';
import { Loading } from '@/components/ui';
import type { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  loading?: boolean;
  className?: string;
}

export function StatCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  loading,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700',
        className
      )}
    >
      {loading ? (
        <div className="h-16 flex items-center justify-center">
          <Loading size="sm" />
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">{title}</span>
            {icon && <span className="text-gray-400">{icon}</span>}
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
          {change !== undefined && (
            <div className="flex items-center gap-1 mt-1">
              <span
                className={cn(
                  'text-sm font-medium',
                  change >= 0 ? 'text-green-500' : 'text-red-500'
                )}
              >
                {change >= 0 ? '+' : ''}
                {change.toFixed(2)}%
              </span>
              {changeLabel && (
                <span className="text-xs text-gray-400">{changeLabel}</span>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
