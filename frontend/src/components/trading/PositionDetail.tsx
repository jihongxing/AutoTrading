import { cn } from '@/utils/cn';
import { formatCurrency, formatPercent, getPnlColor } from '@/utils/format';
import type { Position } from '@/api/trading';

interface PositionDetailProps {
  position: Position | null;
  loading?: boolean;
  className?: string;
}

export function PositionDetail({ position, loading, className }: PositionDetailProps) {
  if (loading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-6 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (!position) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        暂无持仓
      </div>
    );
  }

  const isLong = position.side === 'LONG';
  const rows = [
    { label: '交易对', value: position.symbol },
    { label: '方向', value: position.side, color: isLong ? 'text-green-500' : 'text-red-500' },
    { label: '数量', value: position.quantity.toString() },
    { label: '杠杆', value: `${position.leverage}x` },
    { label: '入场价', value: formatCurrency(position.entryPrice) },
    { label: '当前价', value: formatCurrency(position.currentPrice) },
    { label: '未实现盈亏', value: `${formatCurrency(position.unrealizedPnl)} (${formatPercent(position.unrealizedPnlPct)})`, color: getPnlColor(position.unrealizedPnl) },
  ];

  if (position.liquidationPrice) {
    rows.push({ label: '强平价格', value: formatCurrency(position.liquidationPrice), color: 'text-red-500' });
  }

  return (
    <div className={cn('space-y-3', className)}>
      {rows.map((row) => (
        <div key={row.label} className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">{row.label}</span>
          <span className={cn('font-medium', row.color || 'text-gray-900 dark:text-white')}>
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
}
