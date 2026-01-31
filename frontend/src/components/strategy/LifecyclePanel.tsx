import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import type { StrategyLifecycle, ShadowPerformance } from '@/api/lifecycle';

interface LifecyclePanelProps {
  strategies: {
    active: StrategyLifecycle[];
    degraded: StrategyLifecycle[];
    retired: StrategyLifecycle[];
  };
  shadowStrategies: ShadowPerformance[];
  loading?: boolean;
  onPromote?: (id: string) => void;
  onDemote?: (id: string) => void;
  onRetire?: (id: string) => void;
  className?: string;
}

export function LifecyclePanel({
  strategies,
  shadowStrategies,
  loading,
  onPromote,
  onDemote,
  onRetire,
  className,
}: LifecyclePanelProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    ACTIVE: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    SHADOW: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    DEGRADED: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    RETIRED: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400',
    CANDIDATE: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  };

  const renderStrategyCard = (s: StrategyLifecycle) => (
    <div
      key={s.strategyId}
      className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-900 dark:text-white">{s.strategyId}</span>
        <span className={cn('px-2 py-0.5 text-xs font-medium rounded', statusColors[s.status])}>
          {s.status}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-sm mb-3">
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('strategy.tier')}</span>
          <p className="font-medium text-gray-900 dark:text-white">{s.tier}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('strategy.grade')}</span>
          <p className="font-medium text-gray-900 dark:text-white">{s.healthGrade}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('strategy.weight')}</span>
          <p className="font-medium text-gray-900 dark:text-white">{s.effectiveWeight.toFixed(2)}</p>
        </div>
      </div>
      <div className="flex gap-2">
        {s.status === 'DEGRADED' && onPromote && (
          <button
            onClick={() => onPromote(s.strategyId)}
            className="flex-1 px-3 py-1.5 text-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
          >
            {t('strategy.restore')}
          </button>
        )}
        {s.status === 'ACTIVE' && onDemote && (
          <button
            onClick={() => onDemote(s.strategyId)}
            className="flex-1 px-3 py-1.5 text-sm text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded"
          >
            {t('strategy.demote')}
          </button>
        )}
        {s.status !== 'RETIRED' && onRetire && (
          <button
            onClick={() => onRetire(s.strategyId)}
            className="flex-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
          >
            {t('strategy.retire')}
          </button>
        )}
      </div>
    </div>
  );

  const renderShadowCard = (s: ShadowPerformance) => (
    <div
      key={s.strategyId}
      className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-blue-200 dark:border-blue-800"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-900 dark:text-white">{s.strategyId}</span>
        <span className={cn('px-2 py-0.5 text-xs font-medium rounded', statusColors.SHADOW)}>
          {t('strategy.shadowRunning')}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-2 text-sm">
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('strategy.totalTrades')}</span>
          <p className="font-medium text-gray-900 dark:text-white">{s.totalTrades}</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('strategy.winRate')}</span>
          <p className="font-medium text-gray-900 dark:text-white">{(s.winRate * 100).toFixed(1)}%</p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('strategy.pnl')}</span>
          <p className={cn('font-medium', s.totalPnl >= 0 ? 'text-green-500' : 'text-red-500')}>
            {s.totalPnl >= 0 ? '+' : ''}{s.totalPnl.toFixed(2)}%
          </p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">{t('strategy.drawdown')}</span>
          <p className="font-medium text-red-500">{(s.maxDrawdown * 100).toFixed(1)}%</p>
        </div>
      </div>
    </div>
  );

  const allStrategies = [...strategies.active, ...strategies.degraded];
  const hasData = allStrategies.length > 0 || shadowStrategies.length > 0 || strategies.retired.length > 0;

  if (!hasData) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('strategy.noLifecycleData')}
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {shadowStrategies.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
            {t('strategy.shadowRunning')} ({shadowStrategies.length})
          </h3>
          <div className="space-y-3">
            {shadowStrategies.map(renderShadowCard)}
          </div>
        </div>
      )}

      {strategies.active.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
            {t('strategy.formalRunning')} ({strategies.active.length})
          </h3>
          <div className="space-y-3">
            {strategies.active.map(renderStrategyCard)}
          </div>
        </div>
      )}

      {strategies.degraded.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
            {t('strategy.degraded')} ({strategies.degraded.length})
          </h3>
          <div className="space-y-3">
            {strategies.degraded.map(renderStrategyCard)}
          </div>
        </div>
      )}

      {strategies.retired.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
            {t('strategy.retired')} ({strategies.retired.length})
          </h3>
          <div className="space-y-3 opacity-60">
            {strategies.retired.map(renderStrategyCard)}
          </div>
        </div>
      )}
    </div>
  );
}
