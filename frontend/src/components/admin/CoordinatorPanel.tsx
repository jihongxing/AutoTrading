import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { coordinatorApi, type CoordinatorStatus } from '@/api/coordinator';

export function CoordinatorPanel() {
  const [status, setStatus] = useState<CoordinatorStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const data = await coordinatorApi.getStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  const handleAction = async (action: 'start' | 'stop' | 'enable' | 'disable') => {
    setActionLoading(true);
    try {
      switch (action) {
        case 'start':
          await coordinatorApi.start();
          break;
        case 'stop':
          await coordinatorApi.stop();
          break;
        case 'enable':
          await coordinatorApi.enableTrading();
          break;
        case 'disable':
          await coordinatorApi.disableTrading();
          break;
      }
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle>交易协调器</CardTitle></CardHeader>
        <CardContent><div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" /></CardContent>
      </Card>
    );
  }

  if (error && !status) {
    return (
      <Card>
        <CardHeader><CardTitle>交易协调器</CardTitle></CardHeader>
        <CardContent>
          <p className="text-red-500">{error}</p>
          <Button onClick={loadStatus} className="mt-2">重试</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>交易协调器</CardTitle>
          <div className="flex gap-2">
            <Badge variant={status?.is_running ? 'success' : 'default'}>
              {status?.is_running ? '运行中' : '已停止'}
            </Badge>
            <Badge variant={status?.trading_enabled ? 'warning' : 'default'}>
              {status?.trading_enabled ? '交易启用' : '观察模式'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 状态信息 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold">{status?.metrics?.total_loops || 0}</div>
            <div className="text-sm text-gray-500">循环次数</div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold">{status?.metrics?.claims_generated || 0}</div>
            <div className="text-sm text-gray-500">生成 Claims</div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-green-500">{status?.metrics?.trades_executed || 0}</div>
            <div className="text-sm text-gray-500">执行交易</div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-red-500">{status?.metrics?.risk_rejections || 0}</div>
            <div className="text-sm text-gray-500">风控拒绝</div>
          </div>
        </div>

        {/* 系统状态 */}
        <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
          <span className="text-gray-600 dark:text-gray-400">系统状态</span>
          <span className="font-medium">{status?.system_state?.toUpperCase()}</span>
        </div>

        {/* 最后错误 */}
        {status?.metrics?.last_error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
            <span className="text-red-600 dark:text-red-400 text-sm">{status.metrics.last_error}</span>
          </div>
        )}

        {/* 控制按钮 */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
          {status?.is_running ? (
            <Button
              variant="secondary"
              onClick={() => handleAction('stop')}
              disabled={actionLoading}
            >
              停止协调器
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={() => handleAction('start')}
              disabled={actionLoading}
            >
              启动协调器
            </Button>
          )}

          {status?.trading_enabled ? (
            <Button
              variant="warning"
              onClick={() => handleAction('disable')}
              disabled={actionLoading || !status?.is_running}
            >
              禁用交易
            </Button>
          ) : (
            <Button
              variant="danger"
              onClick={() => handleAction('enable')}
              disabled={actionLoading || !status?.is_running}
            >
              启用交易（危险）
            </Button>
          )}
        </div>

        {/* 警告提示 */}
        {!status?.trading_enabled && (
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded text-sm">
            <span className="text-blue-600 dark:text-blue-400">
              当前为观察模式，系统会分析市场但不会执行实际交易。启用交易前请确保已充分测试。
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
