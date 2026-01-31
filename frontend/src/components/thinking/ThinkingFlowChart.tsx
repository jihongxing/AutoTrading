import type { LoopResult } from '@/api/thinking';

interface Props {
  loop: LoopResult;
}

export function ThinkingFlowChart({ loop }: Props) {
  const steps = [
    {
      id: 'data',
      name: '数据拉取',
      icon: '📊',
      success: loop.step_data?.success,
      info: loop.step_data?.success 
        ? `${loop.step_data.bar_count} 条 | $${loop.step_data.latest_price?.toFixed(2)}`
        : loop.step_data?.error || '失败',
      duration: loop.step_data?.duration_ms,
    },
    {
      id: 'witnesses',
      name: '证人分析',
      icon: '👁️',
      success: (loop.step_witnesses?.claims_generated || 0) > 0,
      skipped: loop.step_witnesses?.skipped,
      info: loop.step_witnesses?.skipped 
        ? '跳过'
        : `${loop.step_witnesses?.active_witnesses || 0}/${loop.step_witnesses?.total_witnesses || 0} 活跃`,
      duration: loop.step_witnesses?.duration_ms,
    },
    {
      id: 'aggregation',
      name: '信号聚合',
      icon: '🔗',
      success: loop.step_aggregation?.is_tradeable,
      skipped: loop.step_aggregation?.skipped,
      info: loop.step_aggregation?.skipped 
        ? '跳过'
        : loop.step_aggregation?.has_veto 
          ? `否决: ${loop.step_aggregation.veto_witness}`
          : loop.step_aggregation?.dominant_direction 
            ? `${loop.step_aggregation.dominant_direction.toUpperCase()} (${(loop.step_aggregation.total_confidence * 100).toFixed(0)}%)`
            : '无方向',
      duration: loop.step_aggregation?.duration_ms,
    },
    {
      id: 'risk',
      name: '风控检查',
      icon: '🛡️',
      success: loop.step_risk?.passed,
      skipped: loop.step_risk?.skipped,
      info: loop.step_risk?.skipped 
        ? '跳过'
        : loop.step_risk?.passed 
          ? `通过 (${loop.step_risk.checks?.length || 0} 项)`
          : `拒绝: ${loop.step_risk?.overall_level}`,
      duration: loop.step_risk?.duration_ms,
    },
    {
      id: 'state',
      name: '状态机',
      icon: '⚙️',
      success: loop.step_state?.can_trade,
      skipped: loop.step_state?.skipped,
      info: loop.step_state?.skipped 
        ? '跳过'
        : `${loop.step_state?.current_state?.toUpperCase()} | ${loop.step_state?.can_trade ? '可交易' : '不可交易'}`,
      duration: loop.step_state?.duration_ms,
    },
    {
      id: 'execution',
      name: '执行决策',
      icon: '🚀',
      success: loop.step_execution?.executed || loop.step_execution?.action === 'simulated',
      skipped: loop.step_execution?.skipped,
      info: loop.step_execution?.skipped 
        ? '跳过'
        : loop.step_execution?.action === 'executed' 
          ? '已执行'
          : loop.step_execution?.action === 'simulated'
            ? '模拟执行'
            : loop.step_execution?.reason || '未执行',
      duration: loop.step_execution?.duration_ms,
    },
  ];

  return (
    <div className="relative">
      {/* 流程图 */}
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            {/* 节点 */}
            <div className="flex flex-col items-center">
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center text-xl
                  ${step.skipped 
                    ? 'bg-gray-200 dark:bg-gray-700' 
                    : step.success 
                      ? 'bg-green-100 dark:bg-green-900/30 border-2 border-green-500' 
                      : 'bg-red-100 dark:bg-red-900/30 border-2 border-red-500'
                  }`}
              >
                {step.icon}
              </div>
              <div className="mt-2 text-xs font-medium text-center">{step.name}</div>
              <div className={`mt-1 text-xs text-center max-w-[80px] truncate
                ${step.skipped ? 'text-gray-400' : step.success ? 'text-green-600' : 'text-red-600'}`}
              >
                {step.info}
              </div>
              {step.duration !== undefined && (
                <div className="text-xs text-gray-400">{step.duration.toFixed(1)}ms</div>
              )}
            </div>
            
            {/* 连接线 */}
            {index < steps.length - 1 && (
              <div className={`w-8 h-0.5 mx-1 ${
                step.success && !step.skipped ? 'bg-green-500' : 'bg-gray-300'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* 总耗时 */}
      <div className="mt-4 text-center text-sm text-gray-500">
        总耗时: {loop.total_duration_ms?.toFixed(2)}ms
      </div>
    </div>
  );
}
