import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { SuggestionCard } from './SuggestionCard';
import type { Suggestion } from '@/api/learning';

interface SuggestionListProps {
  suggestions: Suggestion[];
  loading?: boolean;
  selectedIds?: string[];
  onSelect?: (id: string, selected: boolean) => void;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  actionLoading?: string | null;
  className?: string;
}

export function SuggestionList({
  suggestions,
  loading,
  selectedIds = [],
  onSelect,
  onApprove,
  onReject,
  actionLoading,
  className,
}: SuggestionListProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-48 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('learning.noSuggestions')}
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {suggestions.map((suggestion) => (
        <SuggestionCard
          key={suggestion.suggestionId}
          suggestion={suggestion}
          selected={selectedIds.includes(suggestion.suggestionId)}
          onSelect={onSelect ? (sel) => onSelect(suggestion.suggestionId, sel) : undefined}
          onApprove={onApprove ? () => onApprove(suggestion.suggestionId) : undefined}
          onReject={onReject ? () => onReject(suggestion.suggestionId) : undefined}
          loading={actionLoading === suggestion.suggestionId}
        />
      ))}
    </div>
  );
}
