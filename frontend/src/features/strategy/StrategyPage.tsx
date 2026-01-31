import { useEffect, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, ConfirmDialog, Tabs, TabPanel } from '@/components/ui';
import { StateMachine, WitnessList, WitnessDetail, ClaimHistory, LifecyclePanel } from '@/components/strategy';
import { useWebSocket, type WSMessage } from '@/hooks/useWebSocket';
import { useStrategyStore } from '@/stores/strategyStore';
import { strategyApi, type Witness } from '@/api/strategy';
import { lifecycleApi, type StrategiesResponse, type ShadowPerformance } from '@/api/lifecycle';
import { useMediaQuery } from '@/hooks/useMediaQuery';

export function StrategyPage() {
  const { t } = useTranslation();
  const isMobile = useMediaQuery('(max-width: 1023px)');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('witnesses');
  const [selectedWitness, setSelectedWitness] = useState<Witness | null>(null);
  const [confirmAction, setConfirmAction] = useState<{ type: 'mute' | 'activate'; id: string } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [lifecycleData, setLifecycleData] = useState<StrategiesResponse>({ active: [], degraded: [], retired: [], total: 0 });
  const [shadowData, setShadowData] = useState<ShadowPerformance[]>([]);

  const { stateInfo, witnesses, claims, setStateInfo, setWitnesses, setClaims, updateState, updateWitness } = useStrategyStore();

  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.channel === 'state' && msg.type === 'state_change') {
      updateState((msg.data as any).currentState);
    }
  }, [updateState]);

  useWebSocket({ onMessage: handleWSMessage });

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      setError(null);
      try {
        const [stateRes, witnessRes, claimRes, lifecycleRes, shadowRes] = await Promise.allSettled([
          strategyApi.getState(),
          strategyApi.getWitnesses(),
          strategyApi.getClaims(20),
          lifecycleApi.getStrategies(),
          lifecycleApi.getShadowStrategies(),
        ]);
        if (stateRes.status === 'fulfilled') setStateInfo(stateRes.value);
        if (witnessRes.status === 'fulfilled') setWitnesses(witnessRes.value);
        if (claimRes.status === 'fulfilled') setClaims(claimRes.value.claims);
        if (lifecycleRes.status === 'fulfilled') setLifecycleData(lifecycleRes.value);
        if (shadowRes.status === 'fulfilled') setShadowData(shadowRes.value.strategies);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('common.error'));
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [setStateInfo, setWitnesses, setClaims, t]);

  const handleMute = (id: string) => setConfirmAction({ type: 'mute', id });
  const handleActivate = (id: string) => setConfirmAction({ type: 'activate', id });

  const handleConfirmAction = async () => {
    if (!confirmAction) return;
    setActionLoading(true);
    try {
      const result = confirmAction.type === 'mute'
        ? await strategyApi.muteWitness(confirmAction.id)
        : await strategyApi.activateWitness(confirmAction.id);
      updateWitness(result);
      if (selectedWitness?.witnessId === confirmAction.id) setSelectedWitness(result);
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  };

  const tabs = [
    { id: 'witnesses', label: t('strategy.witnessList') },
    { id: 'lifecycle', label: t('strategy.lifecycle') },
    { id: 'claims', label: t('strategy.claimHistory') },
  ];

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t('strategy.title')}</h1>
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
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t('strategy.title')}</h1>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('strategy.stateMachine')}</CardTitle></CardHeader>
          <CardContent><StateMachine currentState={stateInfo?.currentState || 'IDLE'} /></CardContent>
        </Card>
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
        <TabPanel isActive={activeTab === 'witnesses'}>
          <WitnessList witnesses={witnesses} loading={isLoading} onMute={handleMute} onActivate={handleActivate} onViewDetail={setSelectedWitness} />
        </TabPanel>
        <TabPanel isActive={activeTab === 'lifecycle'}>
          <LifecyclePanel strategies={lifecycleData} shadowStrategies={shadowData} loading={isLoading} />
        </TabPanel>
        <TabPanel isActive={activeTab === 'claims'}>
          <ClaimHistory claims={claims} loading={isLoading} />
        </TabPanel>
        <WitnessDetail witness={selectedWitness} isOpen={!!selectedWitness} onClose={() => setSelectedWitness(null)} onMute={() => selectedWitness && handleMute(selectedWitness.witnessId)} onActivate={() => selectedWitness && handleActivate(selectedWitness.witnessId)} />
        <ConfirmDialog isOpen={!!confirmAction} onClose={() => setConfirmAction(null)} onConfirm={handleConfirmAction} title={confirmAction?.type === 'mute' ? t('strategy.muteWitness') : t('strategy.activateWitness')} message={confirmAction?.type === 'mute' ? t('strategy.muteConfirm') : t('strategy.activateConfirm')} confirmText={confirmAction?.type === 'mute' ? t('strategy.mute') : t('strategy.activate')} variant={confirmAction?.type === 'mute' ? 'warning' : 'default'} loading={actionLoading} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('strategy.title')}</h1>
      <Card>
        <CardHeader><CardTitle>{t('strategy.stateMachine')}</CardTitle></CardHeader>
        <CardContent><StateMachine currentState={stateInfo?.currentState || 'IDLE'} /></CardContent>
      </Card>
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      <TabPanel isActive={activeTab === 'witnesses'}>
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2">
            <Card>
              <CardHeader><CardTitle>{t('strategy.witnessList')}</CardTitle></CardHeader>
              <CardContent><WitnessList witnesses={witnesses} loading={isLoading} onMute={handleMute} onActivate={handleActivate} onViewDetail={setSelectedWitness} /></CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader><CardTitle>{t('strategy.claimHistory')}</CardTitle></CardHeader>
            <CardContent><ClaimHistory claims={claims} loading={isLoading} /></CardContent>
          </Card>
        </div>
      </TabPanel>
      <TabPanel isActive={activeTab === 'lifecycle'}>
        <Card>
          <CardHeader><CardTitle>{t('strategy.lifecycle')}</CardTitle></CardHeader>
          <CardContent><LifecyclePanel strategies={lifecycleData} shadowStrategies={shadowData} loading={isLoading} /></CardContent>
        </Card>
      </TabPanel>
      <TabPanel isActive={activeTab === 'claims'}>
        <Card>
          <CardHeader><CardTitle>{t('strategy.claimHistory')}</CardTitle></CardHeader>
          <CardContent><ClaimHistory claims={claims} loading={isLoading} /></CardContent>
        </Card>
      </TabPanel>
      <WitnessDetail witness={selectedWitness} isOpen={!!selectedWitness} onClose={() => setSelectedWitness(null)} onMute={() => selectedWitness && handleMute(selectedWitness.witnessId)} onActivate={() => selectedWitness && handleActivate(selectedWitness.witnessId)} />
      <ConfirmDialog isOpen={!!confirmAction} onClose={() => setConfirmAction(null)} onConfirm={handleConfirmAction} title={confirmAction?.type === 'mute' ? t('strategy.muteWitness') : t('strategy.activateWitness')} message={confirmAction?.type === 'mute' ? t('strategy.muteConfirm') : t('strategy.activateConfirm')} confirmText={confirmAction?.type === 'mute' ? t('strategy.mute') : t('strategy.activate')} variant={confirmAction?.type === 'mute' ? 'warning' : 'default'} loading={actionLoading} />
    </div>
  );
}
