/**
 * 格式化数字为货币格式
 */
export function formatCurrency(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * 格式化数字为百分比
 */
export function formatPercent(value: number, decimals = 2): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

/**
 * 格式化数字（带千分位）
 */
export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * 格式化时间为相对时间
 */
export function formatRelativeTime(date: string | Date | undefined | null): string {
  if (!date) return '-';
  const target = new Date(date);
  if (isNaN(target.getTime())) return '-';
  
  const now = new Date();
  const diff = now.getTime() - target.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}天前`;
  if (hours > 0) return `${hours}小时前`;
  if (minutes > 0) return `${minutes}分钟前`;
  return '刚刚';
}

/**
 * 格式化日期时间
 */
export function formatDateTime(date: string | Date | undefined | null): string {
  if (!date) return '-';
  const d = new Date(date);
  if (isNaN(d.getTime())) return '-';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

/**
 * 格式化日期
 */
export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(date));
}

/**
 * 获取 PnL 颜色类名
 */
export function getPnlColor(value: number): string {
  if (value > 0) return 'text-green-500';
  if (value < 0) return 'text-red-500';
  return 'text-gray-500';
}

/**
 * 获取状态颜色类名
 */
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    IDLE: 'text-gray-500',
    OBSERVING: 'text-blue-500',
    CLAIMING: 'text-yellow-500',
    POSITIONED: 'text-green-500',
    COOLDOWN: 'text-orange-500',
    LOCKED: 'text-red-500',
  };
  return colors[status] || 'text-gray-500';
}
