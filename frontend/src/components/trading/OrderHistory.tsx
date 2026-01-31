import { useState } from 'react';
import { cn } from '@/utils/cn';
import { formatCurrency, formatDateTime } from '@/utils/format';
import type { Order } from '@/api/trading';

interface OrderHistoryProps {
  orders: Order[];
  loading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  className?: string;
}

export function OrderHistory({
  orders,
  loading,
  hasMore,
  onLoadMore,
  className,
}: OrderHistoryProps) {
  const [loadingMore, setLoadingMore] = useState(false);

  const historyOrders = orders.filter((o) =>
    ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED'].includes(o.status)
  );

  const handleLoadMore = async () => {
    if (!onLoadMore) return;
    setLoadingMore(true);
    try {
      await onLoadMore();
    } finally {
      setLoadingMore(false);
    }
  };

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (historyOrders.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        暂无历史订单
      </div>
    );
  }

  const getStatusStyle = (status: string) => {
    const styles: Record<string, string> = {
      FILLED: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      CANCELED: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400',
      REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      EXPIRED: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    };
    return styles[status] || styles.CANCELED;
  };

  return (
    <div className={cn('space-y-2', className)}>
      {historyOrders.map((order) => (
        <div
          key={order.orderId}
          className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
        >
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-gray-900 dark:text-white">
                {order.symbol}
              </span>
              <span
                className={cn(
                  'px-1.5 py-0.5 text-xs font-medium rounded',
                  order.side === 'BUY'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                )}
              >
                {order.side}
              </span>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <span>{order.filledQuantity} @ {order.avgPrice ? formatCurrency(order.avgPrice) : '-'}</span>
              <span>{formatDateTime(order.createdAt)}</span>
            </div>
          </div>
          <span className={cn('px-2 py-0.5 text-xs font-medium rounded', getStatusStyle(order.status))}>
            {order.status}
          </span>
        </div>
      ))}

      {hasMore && (
        <button
          onClick={handleLoadMore}
          disabled={loadingMore}
          className="w-full py-2 text-sm text-blue-500 hover:text-blue-600 disabled:text-gray-400"
        >
          {loadingMore ? '加载中...' : '加载更多'}
        </button>
      )}
    </div>
  );
}
