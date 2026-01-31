import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui';
import type { WitnessRank } from '@/api/learning';

interface WitnessRankingProps {
  ranking: WitnessRank[];
  loading?: boolean;
  className?: string;
}

export function WitnessRanking({ ranking, loading, className }: WitnessRankingProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (ranking.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('learning.noRanking')}
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {ranking.map((item, index) => (
        <div
          key={item.witnessId}
          className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
        >
          <span
            className={cn(
              'w-6 h-6 flex items-center justify-center rounded-full text-sm font-bold',
              index === 0 ? 'bg-yellow-100 text-yellow-700' :
              index === 1 ? 'bg-gray-200 text-gray-700' :
              index === 2 ? 'bg-orange-100 text-orange-700' :
              'bg-gray-100 text-gray-500'
            )}
          >
            {index + 1}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900 dark:text-white truncate">
                {item.witnessName}
              </span>
              <Badge variant={item.tier === 'TIER1' ? 'tier1' : item.tier === 'TIER2' ? 'tier2' : 'tier3'} size="sm">
                {item.tier}
              </Badge>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {(item.winRate * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-gray-500">{item.sampleCount} {t('learning.samples')}</p>
          </div>
          <span
            className={cn(
              'text-lg font-bold',
              item.grade === 'A' ? 'text-green-500' :
              item.grade === 'B' ? 'text-blue-500' :
              item.grade === 'C' ? 'text-yellow-500' : 'text-red-500'
            )}
          >
            {item.grade}
          </span>
        </div>
      ))}
    </div>
  );
}
