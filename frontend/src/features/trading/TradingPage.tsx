import { useEffect, useCallback, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { KlineChart, type KlineInterval } from '@/components/charts';
import { PositionDetail, ActiveOrders, OrderHistory } from '@/components/trading';
import { useWebSocket, type WSMessage } from '@/hooks/useWebSocket';
import { useTradingStore } from '@/stores/tradingStore';
import { tradingApi } from '@/api/trading';
import { marketApi, type Kline } from '@/api/market';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import type { CandlestickData } from 'lightweight-charts';

const SYMBOL = 'BTCUSDT';

export function TradingPage() {
  const { t } = useTranslation();
  const isMobile = useMediaQuery('(max-width: 1023px)');
  const [interval, setInterval] = useState<KlineInterval>('15m');
  const [klines, setKlines] = useState<Kline[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [, setOrdersPage] = useState(1);
  const [hasMoreOrders, setHasMoreOrders] = useState(true);
  const [noExchange, setNoExchange] = useState(false);

  const { positions, orders, setPositions, setOrders, updatePosition, updateOrder, removeOrder } = useTradingStore();

  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.channel === 'trading') {
      if (msg.type === 'position') updatePosition(msg.data as any);
      else if (msg.type === 'order') {
        if (msg.action === 'delete') removeOrder((msg.data as any).orderId);
        else updateOrder(msg.data as any);
      }
    } else if (msg.channel === 'market' && msg.type === 'kline') {
      const kline = msg.data as Kline;
      setKlines((prev) => {
        const newKlines = [...prev];
        const lastIdx = newKlines.length - 1;
        if (lastIdx >= 0 && newKlines[lastIdx].timestamp === kline.timestamp) {
          newKlines[lastIdx] = kline;
        } else {
          newKlines.push(kline);
          if (newKlines.length > 500) newKlines.shift();
        }
        return newKlines;
      });
    }
  }, [updatePosition, updateOrder, removeOrder]);

  useWebSocket({ onMessage: handleWSMessage });

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      setNoExchange(false);
      try {
        const [posRes, orderRes, klineRes] = await Promise.allSettled([
          tradingApi.getPositions(),
          tradingApi.getOrders({ limit: 20 }),
          marketApi.getKlines(SYMBOL, interval, 200),
        ]);
        if (posRes.status === 'rejected' && posRes.reason?.message?.includes('NO_EXCHANGE')) {
          setNoExchange(true);
        }
        if (posRes.status === 'fulfilled') setPositions(posRes.value.positions, posRes.value.totalUnrealizedPnl);
        if (orderRes.status === 'fulfilled') {
          setOrders(orderRes.value.orders);
          setHasMoreOrders(orderRes.value.orders.length >= 20);
        }
        if (klineRes.status === 'fulfilled') setKlines(klineRes.value.bars);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [interval, setPositions, setOrders]);

  const ExchangePrompt = () => (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-center">
      <p className="text-yellow-800 dark:text-yellow-200 mb-2">{t('dashboard.configExchange')}</p>
      <Link to="/settings" className="text-blue-600 dark:text-blue-400 hover:underline font-medium">{t('dashboard.goToSettings')} →</Link>
    </div>
  );

  const chartData: CandlestickData[] = useMemo(() => {
    return klines.map((k) => ({
      time: (new Date(k.timestamp).getTime() / 1000) as any,
      open: k.open,
      high: k.high,
      low: k.low,
      close: k.close,
    }));
  }, [klines]);

  const handleIntervalChange = (newInterval: KlineInterval) => setInterval(newInterval);
  const handleCancelOrder = async (orderId: string) => {
    await tradingApi.cancelOrder(orderId);
    removeOrder(orderId);
  };
  const handleLoadMoreOrders = async () => {
    const res = await tradingApi.getOrders({ limit: 20 });
    setOrders([...orders, ...res.orders]);
    setHasMoreOrders(res.orders.length >= 20);
    setOrdersPage((p) => p + 1);
  };

  const currentPosition = positions.length > 0 ? positions[0] : null;

  if (isMobile) {
    return (
      <div className="space-y-4 pb-20">
        {noExchange && <ExchangePrompt />}
        <Card>
          <CardContent className="p-2">
            {klines.length > 0 ? (
              <KlineChart data={chartData} interval={interval} onIntervalChange={handleIntervalChange} height={300} />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">{t('common.noData')}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('trading.positionDetail')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? <p className="text-gray-500 text-sm text-center py-4">{t('dashboard.configExchange')}</p> : <PositionDetail position={currentPosition} loading={isLoading} />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('trading.activeOrders')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? <p className="text-gray-500 text-sm text-center py-4">{t('dashboard.configExchange')}</p> : <ActiveOrders orders={orders} loading={isLoading} onCancel={handleCancelOrder} />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">{t('trading.orderHistory')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? <p className="text-gray-500 text-sm text-center py-4">{t('dashboard.configExchange')}</p> : <OrderHistory orders={orders} loading={isLoading} hasMore={hasMoreOrders} onLoadMore={handleLoadMoreOrders} />}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {noExchange && <ExchangePrompt />}
      <Card>
        <CardHeader><CardTitle>BTCUSDT</CardTitle></CardHeader>
        <CardContent>
          {klines.length > 0 ? (
            <KlineChart data={chartData} interval={interval} onIntervalChange={handleIntervalChange} height={400} />
          ) : (
            <div className="h-[400px] flex items-center justify-center text-gray-500">{t('common.noData')}</div>
          )}
        </CardContent>
      </Card>
      <div className="grid grid-cols-3 gap-6">
        <Card>
          <CardHeader><CardTitle>{t('trading.positionDetail')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? <p className="text-gray-500 text-sm text-center py-8">{t('dashboard.configExchange')}</p> : <PositionDetail position={currentPosition} loading={isLoading} />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>{t('trading.activeOrders')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? <p className="text-gray-500 text-sm text-center py-8">{t('dashboard.configExchange')}</p> : <ActiveOrders orders={orders} loading={isLoading} onCancel={handleCancelOrder} />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>{t('trading.orderHistory')}</CardTitle></CardHeader>
          <CardContent>
            {noExchange ? <p className="text-gray-500 text-sm text-center py-8">{t('dashboard.configExchange')}</p> : <OrderHistory orders={orders} loading={isLoading} hasMore={hasMoreOrders} onLoadMore={handleLoadMoreOrders} />}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
