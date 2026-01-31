import { cn } from '@/utils/cn';

interface SkeletonProps {
  variant?: 'text' | 'card' | 'chart' | 'table' | 'circle';
  lines?: number;
  className?: string;
}

export function Skeleton({ variant = 'text', lines = 1, className }: SkeletonProps) {
  const baseClass = 'animate-pulse bg-gray-200 dark:bg-gray-700 rounded';

  switch (variant) {
    case 'card':
      return (
        <div className={cn('p-4 space-y-3', baseClass, className)}>
          <div className="h-4 w-1/3 bg-gray-300 dark:bg-gray-600 rounded" />
          <div className="h-8 w-2/3 bg-gray-300 dark:bg-gray-600 rounded" />
          <div className="h-3 w-full bg-gray-300 dark:bg-gray-600 rounded" />
        </div>
      );
    case 'chart':
      return <div className={cn('h-48', baseClass, className)} />;
    case 'table':
      return (
        <div className={cn('space-y-2', className)}>
          {Array.from({ length: lines }).map((_, i) => (
            <div key={i} className={cn('h-12', baseClass)} />
          ))}
        </div>
      );
    case 'circle':
      return <div className={cn('w-10 h-10 rounded-full', baseClass, className)} />;
    default:
      return (
        <div className={cn('space-y-2', className)}>
          {Array.from({ length: lines }).map((_, i) => (
            <div key={i} className={cn('h-4', baseClass, i === lines - 1 && 'w-3/4')} />
          ))}
        </div>
      );
  }
}
