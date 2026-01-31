import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui';
import type { Witness } from '@/api/strategy';

interface WitnessCardProps {
  witness: Witness;
  onMute?: () => void;
  onActivate?: () => void;
  onViewDetail?: () => void;
  className?: string;
}

export function WitnessCard({
  witness,
  onMute,
  onActivate,
  onViewDetail,
  className,
}: WitnessCardProps) {
  const { t } = useTranslation();
  const tierVariant = witness.tier === 'TIER1' ? 'tier1' : witness.tier === 'TIER2' ? 'tier2' : 'tier3';
  const statusVariant = witness.status === 'ACTIVE' ? 'success' : witness.status === 'MUTED' ? 'default' : 'warning';

  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-100 dark:border-gray-700',
        !witness.isActive && 'opacity-60',
        className
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-gray-900 dark:text-white">{witness.name}</span>
            <Badge variant={tierVariant}>{witness.tier}</Badge>
          </div>
          <Badge variant={statusVariant} size="sm">{witness.status}</Badge>
        </div>
        {witness.health && (
          <span className={cn(
            'text-lg font-bold',
            witness.health.grade === 'A' ? 'text-green-500' :
            witness.health.grade === 'B' ? 'text-blue-500' :
            witness.health.grade === 'C' ? 'text-yellow-500' : 'text-red-500'
          )}>
            {witness.health.grade}
          </span>
        )}
      </div>

      {witness.health && (
        <div className="grid grid-cols-3 gap-2 text-sm mb-3">
          <div>
            <span className="text-gray-500 dark:text-gray-400">{t('strategy.winRate')}</span>
            <p className="font-medium text-gray-900 dark:text-white">
              {(witness.health.winRate * 100).toFixed(1)}%
            </p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">{t('strategy.samples')}</span>
            <p className="font-medium text-gray-900 dark:text-white">
              {witness.health.sampleCount}
            </p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">{t('strategy.weight')}</span>
            <p className="font-medium text-gray-900 dark:text-white">
              {witness.health.weight.toFixed(2)}
            </p>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        {onViewDetail && (
          <button
            onClick={onViewDetail}
            className="flex-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
          >
            {t('strategy.detail')}
          </button>
        )}
        {witness.status === 'ACTIVE' && onMute && (
          <button
            onClick={onMute}
            className="flex-1 px-3 py-1.5 text-sm text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded"
          >
            {t('strategy.mute')}
          </button>
        )}
        {witness.status === 'MUTED' && onActivate && (
          <button
            onClick={onActivate}
            className="flex-1 px-3 py-1.5 text-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
          >
            {t('strategy.activate')}
          </button>
        )}
      </div>
    </div>
  );
}
