import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { formatDateTime } from '@/utils/format';
import type { RiskEvent } from '@/api/risk';

interface RiskEventLogProps {
  events: RiskEvent[];
  loading?: boolean;
  className?: string;
}

export function RiskEventLog({ events, loading, className }: RiskEventLogProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('risk.noEvents')}
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {events.map((event) => (
        <EventItem key={event.eventId} event={event} />
      ))}
    </div>
  );
}

function EventItem({ event }: { event: RiskEvent }) {
  const getSeverityConfig = (severity: RiskEvent['severity']) => {
    switch (severity) {
      case 'critical':
        return { icon: '🔴', bg: 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800' };
      case 'warning':
        return { icon: '🟡', bg: 'bg-yellow-50 dark:bg-yellow-900/10 border-yellow-200 dark:border-yellow-800' };
      default:
        return { icon: '🔵', bg: 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800' };
    }
  };

  const config = getSeverityConfig(event.severity);

  return (
    <div className={cn('p-3 rounded-lg border', config.bg)}>
      <div className="flex items-start gap-2">
        <span className="text-sm">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {event.eventType}
            </span>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {formatDateTime(event.timestamp)}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
            {event.message}
          </p>
        </div>
      </div>
    </div>
  );
}
