import { useTranslation } from 'react-i18next';
import { Modal, Badge, Button } from '@/components/ui';
import type { Witness } from '@/api/strategy';

interface WitnessDetailProps {
  witness: Witness | null;
  isOpen: boolean;
  onClose: () => void;
  onMute?: () => void;
  onActivate?: () => void;
  loading?: boolean;
}

export function WitnessDetail({
  witness,
  isOpen,
  onClose,
  onMute,
  onActivate,
  loading,
}: WitnessDetailProps) {
  const { t } = useTranslation();

  if (!witness) return null;

  const tierVariant = witness.tier === 'TIER1' ? 'tier1' : witness.tier === 'TIER2' ? 'tier2' : 'tier3';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('strategy.witnessDetail')} size="md">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold text-gray-900 dark:text-white">{witness.name}</span>
          <Badge variant={tierVariant}>{witness.tier}</Badge>
        </div>

        {witness.description && (
          <p className="text-sm text-gray-600 dark:text-gray-300">{witness.description}</p>
        )}

        <div className="grid grid-cols-2 gap-4 py-4 border-y border-gray-200 dark:border-gray-700">
          <div>
            <span className="text-sm text-gray-500">{t('strategy.status')}</span>
            <p className="font-medium text-gray-900 dark:text-white">{witness.status}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">{t('strategy.isActive')}</span>
            <p className="font-medium text-gray-900 dark:text-white">
              {witness.isActive ? t('strategy.yes') : t('strategy.no')}
            </p>
          </div>
        </div>

        {witness.health && (
          <div className="space-y-3">
            <h4 className="font-medium text-gray-900 dark:text-white">{t('strategy.healthMetrics')}</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-sm text-gray-500">{t('strategy.winRate')}</span>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {(witness.health.winRate * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500">{t('strategy.sampleCount')}</span>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {witness.health.sampleCount}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500">{t('strategy.weight')}</span>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {witness.health.weight.toFixed(3)}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500">{t('strategy.grade')}</span>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {witness.health.grade}
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="flex gap-3 pt-4">
          {witness.status === 'ACTIVE' && onMute && (
            <Button variant="warning" onClick={onMute} loading={loading} className="flex-1">
              {t('strategy.muteWitness')}
            </Button>
          )}
          {witness.status === 'MUTED' && onActivate && (
            <Button variant="primary" onClick={onActivate} loading={loading} className="flex-1">
              {t('strategy.activateWitness')}
            </Button>
          )}
          <Button variant="ghost" onClick={onClose} className="flex-1">
            {t('common.close')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
