import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { thinkingApi, type LoopResult } from '@/api/thinking';
import { ThinkingTimeline } from '@/components/thinking/ThinkingTimeline';
import { ThinkingFlowChart } from '@/components/thinking/ThinkingFlowChart';

export function ThinkingPage() {
  const [selectedLoop, setSelectedLoop] = useState<LoopResult | null>(null);
  
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['thinking-history'],
    queryFn: () => thinkingApi.getHistory(50),
    refetchInterval: 30000, // 30秒刷新一次
  });

  const getActionColor = (action: string) => {
    switch (action) {
      case 'executed': return 'success';
      case 'simulated': return 'info';
      case 'no_signal': return 'secondary';
      case 'skipped': return 'warning';
      case 'error': return 'danger';
      default: return 'secondary';
    }
  };

  const getActionText = (action: string) => {
    switch (action) {
      case 'executed': return '已执行';
      case 'simulated': return '模拟';
      case 'no_signal': return '无信号';
      case 'skipped': return '跳过';
      case 'error': return '错误';
      default: return action;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">系统思考过程</h1>
        <Button onClick={() => refetch()} disabled={isLoading}>
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧：时间线列表 */}
        <Card>
          <CardHeader>
            <CardTitle>决策历史 ({data?.total || 0} 条)</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-gray-500">加载中...</div>
            ) : !data?.history?.length ? (
              <div className="text-center py-8 text-gray-500">暂无决策记录</div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {data.history.map((loop) => (
                  <div
                    key={loop.loop_id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedLoop?.loop_id === loop.loop_id
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedLoop(loop)}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">#{loop.loop_id}</span>
                      <Badge variant={getActionColor(loop.final_action)}>
                        {getActionText(loop.final_action)}
                      </Badge>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {new Date(loop.timestamp).toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-400 mt-1 truncate">
                      {loop.final_reason}
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-xs">
                      <span className={loop.step_data?.success ? 'text-green-500' : 'text-red-500'}>
                        数据{loop.step_data?.success ? '✓' : '✗'}
                      </span>
                      <span className={loop.step_witnesses?.claims_generated > 0 ? 'text-green-500' : 'text-gray-400'}>
                        证人({loop.step_witnesses?.claims_generated || 0})
                      </span>
                      <span className={loop.step_aggregation?.is_tradeable ? 'text-green-500' : 'text-gray-400'}>
                        聚合{loop.step_aggregation?.is_tradeable ? '✓' : '✗'}
                      </span>
                      <span className={loop.step_risk?.passed ? 'text-green-500' : 'text-red-500'}>
                        风控{loop.step_risk?.passed ? '✓' : '✗'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 右侧：流程图详情 */}
        <Card>
          <CardHeader>
            <CardTitle>
              {selectedLoop ? `决策详情 #${selectedLoop.loop_id}` : '选择一条记录查看详情'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedLoop ? (
              <div className="space-y-6">
                <ThinkingFlowChart loop={selectedLoop} />
                <ThinkingTimeline loop={selectedLoop} />
              </div>
            ) : (
              <div className="text-center py-16 text-gray-500">
                点击左侧列表查看决策详情
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
