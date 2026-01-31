import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { formatCurrency, formatRelativeTime } from '@/utils/format';
import type { Order } from '@/api/trading';

interface OrderListProps {
  orders: Order[];
  loading?: boolean;
  onCancel?: (orderId: string) => void;
  showCancel?: boolean;
  className?: string;
}

export function OrderList({
  orders,
  loading,
  onCancel,
  showCancel = false,
  className,
}: OrderListProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 bg-gray-100 dark:bg-gray-700 rounded animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('dashboard.noOrders')}
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {orders.map((order) => (
        <OrderItem
          key={order.orderId}
          order={order}
          onCancel={onCancel}
          showCancel={showCancel}
        />
      ))}
    </div>
  );
}

interface OrderItemProps {
  order: Order;
  onCancel?: (orderId: string) => void;
  showCancel?: boolean;
}

function OrderItem({ order, onCancel, showCancel }: OrderItemProps) {
  const { t } = useTranslation();
  const isBuy = order.side === 'BUY';
  const isPending = ['NEW', 'PARTIALLY_FILLED'].includes(order.status);

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white">
            {order.symbol}
          </span>
          <span
            className={cn(
              'px-1.5 py-0.5 text-xs font-medium rounded',
              isBuy
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            )}
          >
            {order.side}
          </span>
          <span className="text-xs text-gray-500">{order.orderType}</span>
        </div>
        <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
          <span>
            {order.filledQuantity}/{order.quantity}
          </span>
          {order.price && <span>@ {formatCurrency(order.price)}</span>}
          <span>{formatRelativeTime(order.createdAt)}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <StatusBadge status={order.status} />
        {showCancel && isPending && onCancel && (
          <button
            onClick={() => onCancel(order.orderId)}
            className="px-2 py-1 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
          >
            {t('dashboard.cancel')}
          </button>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    NEW: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    PARTIALLY_FILLED: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    FILLED: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    CANCELED: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400',
    REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={cn('px-2 py-0.5 text-xs font-medium rounded', colors[status] || colors.NEW)}>
      {status}
    </span>
  );
}
