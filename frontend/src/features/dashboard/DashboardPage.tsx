import { useEffect, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { StatCard, OrderList, RiskOverview, SystemStatus } from '@/components/dashboard';
import { PnLChart } from '@/components/charts';
import { useWebSocket, type WSMessage } from '@/hooks/useWebSocket';
import { useTradingStore } from '@/stores/tradingStore';
import { useSystemStore } from '@/stores/systemStore';
import { useRiskStore } from '@/stores/riskStore';
import { tradingApi, type RiskStatus } from '@/api/trading';
import { systemApi } from '@/api/system';
import { formatCurrency } from '@/utils/format';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { Link } from 'react-router-dom';

type PnLPeriod = '7d' | '30d' | 'all';

export function DashboardPage() {
  const { t } = useTranslation();
  const isMobile = useMediaQuery('(max-width: 1023px)');
  const [pnlPeriod, setPnlPeriod] = useState<PnLPeriod>('7d');
  const [isLoading, setIsLoading] = useState(true);
  const [risk, setRisk] = useState<RiskStatus | null>(null);
  const [noExchange, setNoExchange] = useState(false);

  const { positions, orders, profitHistory, setPositions, setOrders, setProfitHistory, updatePosition, updateOrder, removeOrder } = useTradingStore();
  const { state, account, setState, setAccount, updateState } = useSystemStore();
  const { updateStatus } = useRiskStore();

  const handleWSMessage = useCallback((msg: WSMessage) => {
    switch (msg.channel) {
      case 'trading':
        if (msg.type === 'position') updatePosition(msg.data as any);
        else if (msg.type === 'order') {
          if (msg.action === 'delete') removeOrder((msg.data as any).orderId);
          else updateOrder(msg.data as any);
        }
        break;
      case 'state':
        if (msg.type === 'state_change') updateState(msg.data as any);
        break;
      case 'risk':
        if (msg.type === 'metrics') {
          updateStatus(msg.data as any);
          setRisk((prev) => prev ? { ...prev, ...(msg.data as any) } : null);
        }
        break;
    }
  }, [updatePosition, updateOrder, removeOrder, updateState, updateStatus]);

  const { isConnected } = useWebSocket({
    onMessage: handleWSMessage,
  });

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      setNoExchange(false);
      try {
        const [posRes, orderRes, profitRes, stateRes, accountRes, riskRes] = await Promise.allSettled([
          tradingApi.getPositions(),
          tradingApi.getOrders({ limit: 10 }),
          tradingApi.getProfit(pnlPeriod),
          systemApi.getState(),
          systemApi.getAccount(),
          tradingApi.getRisk(),
        ]);

        if (posRes.status === 'rejected' && posRes.reason?.message?.includes('NO_EXCHANGE')) {
          setNoExchange(true);
        }
        if (posRes.status === 'fulfilled') setPositions(posRes.value.positions, posRes.value.totalUnrealizedPnl);
        if (orderRes.status === 'fulfilled') setOrders(orderRes.value.orders);
        if (profitRes.status === 'fulfilled') setProfitHistory(profitRes.value);
        if (stateRes.status === 'fulfilled') setState(stateRes.value);
        if (accountRes.status === 'fulfilled') setAccount(accountRes.value);
        if (riskRes.status === 'fulfilled') setRisk(riskRes.value);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [pnlPeriod, setPositions, setOrders, setProfitHistory, setState, setAccount]);

  const handlePeriodChange = (period: PnLPeriod) => setPnlPeriod(period);

  const ExchangePrompt = () => (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-center">
      <p className="text-yellow-800 dark:text-yellow-200 mb-2">{t('dashboard.configExchange')}</p>
      <Link to="/settings" className="text-blue-600 dark:text-blue-400 hover:underline font-medium">
        {t('dashboard.goToSettings')} →
      </Link>
    </div>
  );

  if (isMobile) {
    return (
      <div className="space-y-4 pb-20">
        {noExchange && <ExchangePrompt />}
        <div className="grid grid-cols-2 gap-3">
          <StatCard title={t('dashboard.accountBalance')} value={account ? formatCurrency(account.balance) : '-'} loading={isLoading} />
          <StatCard title={t('dashboard.todayPnl')} value={account ? formatCurrency(account.todayPnl) : '-'} change={account?.todayPnlPct} loading={isLoading} />
        </div>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('dashboard.systemState')}</CardTitle></CardHeader>
          <CardContent><SystemStatus state={state} wsConnected={isConnected} loading={isLoading} /></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('dashboard.currentPosition')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? (
              <p className="text-gray-500 text-sm text-center py-4">{t('dashboard.configExchange')}</p>
            ) : positions.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-4">{t('dashboard.noPosition')}</p>
            ) : (
              <div className="space-y-2">
                {positions.map((p, i) => (
                  <div key={i} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="font-medium">{p.symbol}</span>
                    <span className={p.unrealizedPnl >= 0 ? 'text-green-500' : 'text-red-500'}>{formatCurrency(p.unrealizedPnl)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('dashboard.profitCurve')}</CardTitle></CardHeader>
          <CardContent><PnLChart data={profitHistory} period={pnlPeriod} onPeriodChange={handlePeriodChange} height={180} /></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('dashboard.riskMetrics')}</CardTitle></CardHeader>
          <CardContent><RiskOverview risk={risk} loading={isLoading} /></CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {noExchange && <ExchangePrompt />}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title={t('dashboard.accountBalance')} value={account ? formatCurrency(account.balance) : '-'} change={account?.todayPnlPct} changeLabel={t('dashboard.todayPnl')} loading={isLoading} />
        <StatCard title={t('dashboard.todayPnl')} value={account ? formatCurrency(account.todayPnl) : '-'} change={account?.todayPnlPct} loading={isLoading} />
        <StatCard title={t('dashboard.currentPosition')} value={positions.length > 0 ? positions[0].symbol : t('dashboard.noPosition')} loading={isLoading} />
        <StatCard title={t('dashboard.systemState')} value={state?.currentState || 'UNKNOWN'} loading={isLoading} />
      </div>
      <Card>
        <CardHeader><CardTitle>{t('dashboard.profitCurve')}</CardTitle></CardHeader>
        <CardContent><PnLChart data={profitHistory} period={pnlPeriod} onPeriodChange={handlePeriodChange} height={256} /></CardContent>
      </Card>
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>{t('dashboard.recentOrders')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? (
              <p className="text-gray-500 text-sm text-center py-8">{t('dashboard.configExchange')}</p>
            ) : (
              <OrderList orders={orders.slice(0, 5)} loading={isLoading} />
            )}
          </CardContent>
        </Card>
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>{t('dashboard.riskMetrics')}</CardTitle></CardHeader>
            <CardContent><RiskOverview risk={risk} loading={isLoading} /></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>{t('dashboard.systemState')}</CardTitle></CardHeader>
            <CardContent><SystemStatus state={state} wsConnected={isConnected} loading={isLoading} /></CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
