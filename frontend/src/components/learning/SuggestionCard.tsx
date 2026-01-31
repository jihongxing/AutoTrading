import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { Badge, Button } from '@/components/ui';
import { formatDateTime } from '@/utils/format';
import type { Suggestion } from '@/api/learning';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onApprove?: () => void;
  onReject?: () => void;
  loading?: boolean;
  selected?: boolean;
  onSelect?: (selected: boolean) => void;
  className?: string;
}

export function SuggestionCard({
  suggestion,
  onApprove,
  onReject,
  loading,
  selected,
  onSelect,
  className,
}: SuggestionCardProps) {
  const { t } = useTranslation();
  const isPending = suggestion.status === 'PENDING';
  const statusVariant = suggestion.status === 'APPROVED' ? 'success' : suggestion.status === 'REJECTED' ? 'danger' : 'warning';

  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border',
        selected ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-100 dark:border-gray-700',
        className
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {onSelect && isPending && (
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => onSelect(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300"
            />
          )}
          <span className="font-semibold text-gray-900 dark:text-white">{suggestion.paramName}</span>
          <Badge variant={statusVariant}>{suggestion.status}</Badge>
        </div>
        <span className="text-xs text-gray-500">{formatDateTime(suggestion.createdAt)}</span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <span className="text-sm text-gray-500">{t('learning.currentValue')}</span>
          <p className="font-medium text-gray-900 dark:text-white">{suggestion.currentValue}</p>
        </div>
        <div>
          <span className="text-sm text-gray-500">{t('learning.suggestedValue')}</span>
          <p className="font-medium text-blue-600 dark:text-blue-400">{suggestion.suggestedValue}</p>
        </div>
      </div>

      <div className="mb-3">
        <span className="text-sm text-gray-500">{t('learning.action')}</span>
        <p className="text-sm text-gray-900 dark:text-white">{suggestion.action}</p>
      </div>

      <div className="mb-3">
        <span className="text-sm text-gray-500">{t('learning.reason')}</span>
        <p className="text-sm text-gray-600 dark:text-gray-300">{suggestion.reason}</p>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">{t('learning.confidence')}:</span>
          <span
            className={cn(
              'text-sm font-medium',
              suggestion.confidence >= 0.8 ? 'text-green-500' :
              suggestion.confidence >= 0.6 ? 'text-yellow-500' : 'text-red-500'
            )}
          >
            {(suggestion.confidence * 100).toFixed(0)}%
          </span>
        </div>

        {isPending && suggestion.requiresApproval && (onApprove || onReject) && (
          <div className="flex gap-2">
            {onReject && (
              <Button size="sm" variant="ghost" onClick={onReject} disabled={loading}>
                {t('learning.reject')}
              </Button>
            )}
            {onApprove && (
              <Button size="sm" variant="primary" onClick={onApprove} loading={loading}>
                {t('learning.approve')}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
