import { useState } from 'react';
import type { LoopResult } from '@/api/thinking';

interface Props {
  loop: LoopResult;
}

export function ThinkingTimeline({ loop }: Props) {
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  const toggleStep = (step: string) => {
    setExpandedStep(expandedStep === step ? null : step);
  };

  return (
    <div className="space-y-3">
      {/* Step 1: 数据拉取 */}
      <TimelineItem
        step="1"
        title="数据拉取"
        success={loop.step_data?.success}
        expanded={expandedStep === 'data'}
        onToggle={() => toggleStep('data')}
        summary={loop.step_data?.success 
          ? `获取 ${loop.step_data.bar_count} 条K线，最新价 $${loop.step_data.latest_price?.toFixed(2)}`
          : loop.step_data?.error || '失败'
        }
      >
        <div className="text-sm space-y-1">
          <div>交易对: {loop.step_data?.symbol}</div>
          <div>周期: {loop.step_data?.interval}</div>
          <div>K线数量: {loop.step_data?.bar_count}</div>
          <div>最新价格: ${loop.step_data?.latest_price?.toFixed(2)}</div>
          <div>耗时: {loop.step_data?.duration_ms?.toFixed(2)}ms</div>
        </div>
      </TimelineItem>

      {/* Step 2: 证人分析 */}
      <TimelineItem
        step="2"
        title="证人分析"
        success={(loop.step_witnesses?.claims_generated || 0) > 0}
        skipped={loop.step_witnesses?.skipped}
        expanded={expandedStep === 'witnesses'}
        onToggle={() => toggleStep('witnesses')}
        summary={loop.step_witnesses?.skipped 
          ? '跳过'
          : `${loop.step_witnesses?.active_witnesses || 0}/${loop.step_witnesses?.total_witnesses || 0} 证人活跃，生成 ${loop.step_witnesses?.claims_generated || 0} 个信号`
        }
      >
        <div className="text-sm space-y-2">
          {loop.step_witnesses?.witnesses?.map((w) => (
            <div 
              key={w.witness_id}
              className={`p-2 rounded ${w.has_claim ? 'bg-green-50 dark:bg-green-900/20' : 'bg-gray-50 dark:bg-gray-800'}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{w.witness_name}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  w.tier === 'TIER1' ? 'bg-blue-100 text-blue-700' :
                  w.tier === 'TIER2' ? 'bg-purple-100 text-purple-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {w.tier}
                </span>
              </div>
              {w.has_claim ? (
                <div className="mt-1 text-xs">
                  <span className={w.direction === 'long' ? 'text-green-600' : 'text-red-600'}>
                    {w.direction?.toUpperCase()}
                  </span>
                  <span className="mx-2">|</span>
                  <span>置信度: {(w.confidence * 100).toFixed(0)}%</span>
                  <span className="mx-2">|</span>
                  <span>{w.claim_type}</span>
                </div>
              ) : (
                <div className="mt-1 text-xs text-gray-500">{w.reason}</div>
              )}
            </div>
          ))}
        </div>
      </TimelineItem>

      {/* Step 3: 信号聚合 */}
      <TimelineItem
        step="3"
        title="信号聚合"
        success={loop.step_aggregation?.is_tradeable}
        skipped={loop.step_aggregation?.skipped}
        expanded={expandedStep === 'aggregation'}
        onToggle={() => toggleStep('aggregation')}
        summary={loop.step_aggregation?.skipped 
          ? '跳过'
          : loop.step_aggregation?.has_veto 
            ? `被否决 (${loop.step_aggregation.veto_witness})`
            : loop.step_aggregation?.is_tradeable
              ? `可交易: ${loop.step_aggregation.dominant_direction?.toUpperCase()} (${(loop.step_aggregation.total_confidence * 100).toFixed(0)}%)`
              : loop.step_aggregation?.reason || '不可交易'
        }
      >
        <div className="text-sm space-y-1">
          <div>总信号数: {loop.step_aggregation?.total_claims}</div>
          <div>是否被否决: {loop.step_aggregation?.has_veto ? '是' : '否'}</div>
          {loop.step_aggregation?.veto_witness && (
            <div>否决证人: {loop.step_aggregation.veto_witness}</div>
          )}
          <div>主导方向: {loop.step_aggregation?.dominant_direction?.toUpperCase() || '无'}</div>
          <div>总置信度: {((loop.step_aggregation?.total_confidence || 0) * 100).toFixed(0)}%</div>
          <div>冲突解决: {loop.step_aggregation?.resolution || '无'}</div>
          <div>可交易: {loop.step_aggregation?.is_tradeable ? '是' : '否'}</div>
          <div>原因: {loop.step_aggregation?.reason}</div>
        </div>
      </TimelineItem>

      {/* Step 4: 风控检查 */}
      <TimelineItem
        step="4"
        title="风控检查"
        success={loop.step_risk?.passed}
        skipped={loop.step_risk?.skipped}
        expanded={expandedStep === 'risk'}
        onToggle={() => toggleStep('risk')}
        summary={loop.step_risk?.skipped 
          ? '跳过'
          : loop.step_risk?.passed 
            ? `通过 (${loop.step_risk.checks?.length || 0} 项检查)`
            : `拒绝 - ${loop.step_risk?.overall_level}`
        }
      >
        <div className="text-sm space-y-2">
          <div>整体级别: {loop.step_risk?.overall_level}</div>
          <div className="space-y-1">
            {loop.step_risk?.checks?.map((check, i) => (
              <div 
                key={i}
                className={`p-2 rounded flex items-center justify-between ${
                  check.passed ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'
                }`}
              >
                <span>{check.name}</span>
                <span className={check.passed ? 'text-green-600' : 'text-red-600'}>
                  {check.passed ? '✓' : '✗'} {check.reason}
                </span>
              </div>
            ))}
          </div>
        </div>
      </TimelineItem>

      {/* Step 5: 状态机判定 */}
      <TimelineItem
        step="5"
        title="状态机判定"
        success={loop.step_state?.can_trade}
        skipped={loop.step_state?.skipped}
        expanded={expandedStep === 'state'}
        onToggle={() => toggleStep('state')}
        summary={loop.step_state?.skipped 
          ? '跳过'
          : `${loop.step_state?.current_state?.toUpperCase()} → ${loop.step_state?.can_trade ? '允许交易' : '禁止交易'}`
        }
      >
        <div className="text-sm space-y-1">
          <div>当前状态: {loop.step_state?.current_state?.toUpperCase()}</div>
          <div>可以交易: {loop.step_state?.can_trade ? '是' : '否'}</div>
          {loop.step_state?.new_state && (
            <div>新状态: {loop.step_state.new_state}</div>
          )}
          <div>原因: {loop.step_state?.reason}</div>
        </div>
      </TimelineItem>

      {/* Step 6: 执行决策 */}
      <TimelineItem
        step="6"
        title="执行决策"
        success={loop.step_execution?.executed || loop.step_execution?.action === 'simulated'}
        skipped={loop.step_execution?.skipped}
        expanded={expandedStep === 'execution'}
        onToggle={() => toggleStep('execution')}
        summary={loop.step_execution?.skipped 
          ? '跳过'
          : loop.step_execution?.action === 'executed'
            ? '已执行交易'
            : loop.step_execution?.action === 'simulated'
              ? '模拟执行'
              : loop.step_execution?.reason || '未执行'
        }
      >
        <div className="text-sm space-y-1">
          <div>应该执行: {loop.step_execution?.should_execute ? '是' : '否'}</div>
          <div>实际执行: {loop.step_execution?.executed ? '是' : '否'}</div>
          <div>动作: {loop.step_execution?.action}</div>
          {loop.step_execution?.order_id && (
            <div>订单ID: {loop.step_execution.order_id}</div>
          )}
          <div>原因: {loop.step_execution?.reason}</div>
        </div>
      </TimelineItem>
    </div>
  );
}

interface TimelineItemProps {
  step: string;
  title: string;
  success?: boolean;
  skipped?: boolean;
  expanded: boolean;
  onToggle: () => void;
  summary: string;
  children: React.ReactNode;
}

function TimelineItem({ step, title, success, skipped, expanded, onToggle, summary, children }: TimelineItemProps) {
  return (
    <div className="relative pl-8">
      {/* 时间线 */}
      <div className="absolute left-0 top-0 bottom-0 w-6 flex flex-col items-center">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white
          ${skipped ? 'bg-gray-400' : success ? 'bg-green-500' : 'bg-red-500'}`}
        >
          {step}
        </div>
        <div className="flex-1 w-0.5 bg-gray-200 dark:bg-gray-700" />
      </div>

      {/* 内容 */}
      <div 
        className={`p-3 rounded-lg border cursor-pointer transition-colors
          ${skipped 
            ? 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700' 
            : success 
              ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800' 
              : 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'
          }`}
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <span className="font-medium">{title}</span>
          <span className="text-xs">{expanded ? '▼' : '▶'}</span>
        </div>
        <div className={`text-sm mt-1 ${skipped ? 'text-gray-500' : success ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
          {summary}
        </div>
        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
