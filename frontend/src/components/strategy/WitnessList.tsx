import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { WitnessCard } from './WitnessCard';
import type { Witness } from '@/api/strategy';

interface WitnessListProps {
  witnesses: Witness[];
  loading?: boolean;
  onMute?: (id: string) => void;
  onActivate?: (id: string) => void;
  onViewDetail?: (witness: Witness) => void;
  className?: string;
}

export function WitnessList({
  witnesses,
  loading,
  onMute,
  onActivate,
  onViewDetail,
  className,
}: WitnessListProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (witnesses.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('strategy.noWitness')}
      </div>
    );
  }

  const grouped = {
    TIER1: witnesses.filter((w) => w.tier === 'TIER1'),
    TIER2: witnesses.filter((w) => w.tier === 'TIER2'),
    TIER3: witnesses.filter((w) => w.tier === 'TIER3'),
  };

  const tierLabels: Record<string, string> = {
    TIER1: t('strategy.coreWitness'),
    TIER2: t('strategy.auxWitness'),
    TIER3: t('strategy.vetoWitness'),
  };

  return (
    <div className={cn('space-y-6', className)}>
      {(['TIER1', 'TIER2', 'TIER3'] as const).map((tier) => {
        if (grouped[tier].length === 0) return null;
        return (
          <div key={tier}>
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
              {tier} - {tierLabels[tier]}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {grouped[tier].map((witness) => (
                <WitnessCard
                  key={witness.witnessId}
                  witness={witness}
                  onMute={onMute ? () => onMute(witness.witnessId) : undefined}
                  onActivate={onActivate ? () => onActivate(witness.witnessId) : undefined}
                  onViewDetail={onViewDetail ? () => onViewDetail(witness) : undefined}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
