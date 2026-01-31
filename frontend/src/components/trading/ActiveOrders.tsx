import { useState } from 'react';
import { cn } from '@/utils/cn';
import { formatCurrency, formatDateTime } from '@/utils/format';
import type { Order } from '@/api/trading';

interface ActiveOrdersProps {
  orders: Order[];
  loading?: boolean;
  onCancel?: (orderId: string) => Promise<void>;
  className?: string;
}

export function ActiveOrders({ orders, loading, onCancel, className }: ActiveOrdersProps) {
  const [cancelingId, setCancelingId] = useState<string | null>(null);

  const activeOrders = orders.filter((o) => ['NEW', 'PARTIALLY_FILLED'].includes(o.status));

  const handleCancel = async (orderId: string) => {
    if (!onCancel) return;
    setCancelingId(orderId);
    try {
      await onCancel(orderId);
    } finally {
      setCancelingId(null);
    }
  };

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        {[1, 2].map((i) => (
          <div key={i} className="h-20 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (activeOrders.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        暂无活跃订单
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {activeOrders.map((order) => (
        <div
          key={order.orderId}
          className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
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
              <span className="text-xs text-gray-500">{order.orderType}</span>
            </div>
            {onCancel && (
              <button
                onClick={() => handleCancel(order.orderId)}
                disabled={cancelingId === order.orderId}
                className={cn(
                  'px-2 py-1 text-xs rounded transition-colors',
                  cancelingId === order.orderId
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                )}
              >
                {cancelingId === order.orderId ? '撤销中...' : '撤销'}
              </button>
            )}
          </div>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div>
              <span className="text-gray-500">数量</span>
              <p className="text-gray-900 dark:text-white">
                {order.filledQuantity}/{order.quantity}
              </p>
            </div>
            <div>
              <span className="text-gray-500">价格</span>
              <p className="text-gray-900 dark:text-white">
                {order.price ? formatCurrency(order.price) : '市价'}
              </p>
            </div>
            <div>
              <span className="text-gray-500">时间</span>
              <p className="text-gray-900 dark:text-white">
                {formatDateTime(order.createdAt)}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
