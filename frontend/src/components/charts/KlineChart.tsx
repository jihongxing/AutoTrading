import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, type IChartApi, type CandlestickData, ColorType, CandlestickSeries } from 'lightweight-charts';
import { cn } from '@/utils/cn';

export type KlineInterval = '1m' | '5m' | '15m' | '1h' | '4h' | '1d';

export interface TradeMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'arrowUp' | 'arrowDown' | 'circle';
  text: string;
}

interface KlineChartProps {
  data: CandlestickData[];
  interval: KlineInterval;
  trades?: TradeMarker[];
  onIntervalChange?: (interval: KlineInterval) => void;
  height?: number;
  className?: string;
}

const INTERVALS: { value: KlineInterval; label: string }[] = [
  { value: '1m', label: '1分' },
  { value: '5m', label: '5分' },
  { value: '15m', label: '15分' },
  { value: '1h', label: '1时' },
  { value: '4h', label: '4时' },
  { value: '1d', label: '1天' },
];

export function KlineChart({
  data,
  interval,
  trades,
  onIntervalChange,
  height = 400,
  className,
}: KlineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<any>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const initChart = useCallback(() => {
    if (!containerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: isFullscreen ? window.innerHeight - 60 : height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries as any;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
          height: isFullscreen ? window.innerHeight - 60 : height,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [height, isFullscreen]);

  useEffect(() => {
    const cleanup = initChart();
    return () => {
      cleanup?.();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [initChart]);

  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      (seriesRef.current as any).setData(data);
      
      if (trades && trades.length > 0) {
        (seriesRef.current as any).setMarkers(
          trades.map((t) => ({
            time: t.time as any,
            position: t.position,
            color: t.color,
            shape: t.shape,
            text: t.text,
          }))
        );
      }

      chartRef.current?.timeScale().fitContent();
    }
  }, [data, trades]);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div
      className={cn(
        'relative',
        isFullscreen && 'fixed inset-0 z-50 bg-gray-900 p-4',
        className
      )}
    >
      {onIntervalChange && (
        <div className="flex items-center justify-between mb-2">
          <div className="flex gap-1">
            {INTERVALS.map((i) => (
              <button
                key={i.value}
                onClick={() => onIntervalChange(i.value)}
                className={cn(
                  'px-2 py-1 text-xs rounded transition-colors',
                  interval === i.value
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                )}
              >
                {i.label}
              </button>
            ))}
          </div>
          <button
            onClick={toggleFullscreen}
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded"
            title={isFullscreen ? '退出全屏' : '全屏'}
          >
            {isFullscreen ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              </svg>
            )}
          </button>
        </div>
      )}
      <div
        ref={containerRef}
        style={{ height: isFullscreen ? 'calc(100vh - 60px)' : height }}
      />
    </div>
  );
}
