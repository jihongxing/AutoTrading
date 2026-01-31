import { useEffect, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { RiskStatusBadge, RiskMetricsGrid, DrawdownChart, RiskEventLog } from '@/components/risk';
import { useWebSocket, type WSMessage } from '@/hooks/useWebSocket';
import { useRiskStore } from '@/stores/riskStore';
import { riskApi } from '@/api/risk';
import { useMediaQuery } from '@/hooks/useMediaQuery';

export function RiskPage() {
  const { t } = useTranslation();
  const isMobile = useMediaQuery('(max-width: 1023px)');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawdownData, setDrawdownData] = useState<{ date: string; drawdown: number }[]>([]);

  const { status, events, setStatus, setEvents, updateStatus, addEvent } = useRiskStore();

  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.channel === 'risk') {
      if (msg.type === 'metrics') updateStatus(msg.data as any);
      else if (msg.type === 'event') addEvent(msg.data as any);
    }
  }, [updateStatus, addEvent]);

  useWebSocket({ onMessage: handleWSMessage });

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      setError(null);
      try {
        const [statusRes, eventsRes] = await Promise.allSettled([
          riskApi.getStatus(),
          riskApi.getEvents(50),
        ]);
        if (statusRes.status === 'fulfilled') setStatus(statusRes.value);
        if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value.events);
        const mockDrawdown = Array.from({ length: 30 }, (_, i) => ({
          date: new Date(Date.now() - (29 - i) * 86400000).toISOString(),
          drawdown: Math.random() * 5 + (i > 20 ? 2 : 0),
        }));
        setDrawdownData(mockDrawdown);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('common.error'));
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [setStatus, setEvents, t]);

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t('risk.title')}</h1>
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-red-500">{error}</p>
            <button onClick={() => window.location.reload()} className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">{t('common.retry')}</button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isMobile) {
    return (
      <div className="space-y-4 pb-20">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t('risk.title')}</h1>
          <RiskStatusBadge level={status?.level || 'UNKNOWN'} isLocked={status?.isLocked} />
        </div>
        {status?.isLocked && status.lockReason && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-700 dark:text-red-400">🔒 {t('risk.lockReason')}: {status.lockReason}</p>
          </div>
        )}
        <RiskMetricsGrid status={status} loading={isLoading} />
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('risk.drawdownChart')}</CardTitle></CardHeader>
          <CardContent><DrawdownChart data={drawdownData} height={180} /></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('risk.riskEvents')}</CardTitle></CardHeader>
          <CardContent><RiskEventLog events={(events || []).slice(0, 10)} loading={isLoading} /></CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('risk.title')}</h1>
        <RiskStatusBadge level={status?.level || 'UNKNOWN'} isLocked={status?.isLocked} />
      </div>
      {status?.isLocked && status.lockReason && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <p className="text-red-700 dark:text-red-400">🔒 {t('risk.locked')}: {status.lockReason}</p>
        </div>
      )}
      <RiskMetricsGrid status={status} loading={isLoading} />
      <Card>
        <CardHeader><CardTitle>{t('risk.drawdownChart')}</CardTitle></CardHeader>
        <CardContent><DrawdownChart data={drawdownData} maxDrawdown={status?.maxDrawdown || 20} height={250} /></CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>{t('risk.riskEvents')}</CardTitle></CardHeader>
        <CardContent><RiskEventLog events={events || []} loading={isLoading} /></CardContent>
      </Card>
    </div>
  );
}
