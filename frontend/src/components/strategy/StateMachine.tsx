import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';

interface StateMachineProps {
  currentState: string;
  stateHistory?: { state: string; timestamp: string }[];
  className?: string;
}

export function StateMachine({ currentState, className }: StateMachineProps) {
  const { t } = useTranslation();

  const STATES = [
    { id: 'IDLE', label: t('strategy.stateIdle'), icon: '⚪' },
    { id: 'OBSERVING', label: t('strategy.stateObserving'), icon: '🔵' },
    { id: 'CLAIMING', label: t('strategy.stateClaiming'), icon: '🟡' },
    { id: 'POSITIONED', label: t('strategy.statePositioned'), icon: '🟢' },
    { id: 'COOLDOWN', label: t('strategy.stateCooldown'), icon: '🟠' },
    { id: 'LOCKED', label: t('strategy.stateLocked'), icon: '🔴' },
  ];

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {STATES.map((state) => {
        const isActive = state.id === currentState;
        return (
          <div
            key={state.id}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all',
              isActive
                ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700 ring-2 ring-blue-500/30'
                : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 opacity-50'
            )}
          >
            <span className="text-lg">{state.icon}</span>
            <span
              className={cn(
                'text-sm font-medium',
                isActive ? 'text-blue-700 dark:text-blue-300' : 'text-gray-500'
              )}
            >
              {state.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
