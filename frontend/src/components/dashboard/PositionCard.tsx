import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { formatCurrency, formatPercent, getPnlColor } from '@/utils/format';
import type { Position } from '@/api/trading';

interface PositionCardProps {
  position: Position;
  className?: string;
}

export function PositionCard({ position, className }: PositionCardProps) {
  const { t } = useTranslation();
  const isLong = position.side === 'LONG';

  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700',
        className
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-900 dark:text-white">
            {position.symbol}
          </span>
          <span
            className={cn(
              'px-2 py-0.5 text-xs font-medium rounded',
              isLong
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            )}
          >
            {position.side}
          </span>
        </div>
        <span className="text-sm text-gray-500">{position.leverage}x</span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('dashboard.quantity')}</span>
          <p className="font-medium text-gray-900 dark:text-white">
            {position.quantity}
          </p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('dashboard.entryPrice')}</span>
          <p className="font-medium text-gray-900 dark:text-white">
            {formatCurrency(position.entryPrice)}
          </p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('dashboard.currentPrice')}</span>
          <p className="font-medium text-gray-900 dark:text-white">
            {formatCurrency(position.currentPrice)}
          </p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('dashboard.unrealizedPnl')}</span>
          <p className={cn('font-medium', getPnlColor(position.unrealizedPnl))}>
            {formatCurrency(position.unrealizedPnl)}
            <span className="text-xs ml-1">
              ({formatPercent(position.unrealizedPnlPct)})
            </span>
          </p>
        </div>
      </div>

      {position.liquidationPrice && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <span className="text-xs text-gray-500">{t('dashboard.liquidationPrice')}: </span>
          <span className="text-xs text-red-500 font-medium">
            {formatCurrency(position.liquidationPrice)}
          </span>
        </div>
      )}
    </div>
  );
}

interface PositionListProps {
  positions: Position[];
  loading?: boolean;
  className?: string;
}

export function PositionList({ positions, loading, className }: PositionListProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-3', className)}>
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-32 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('dashboard.noPosition')}
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {positions.map((pos) => (
        <PositionCard key={pos.symbol} position={pos} />
      ))}
    </div>
  );
}
