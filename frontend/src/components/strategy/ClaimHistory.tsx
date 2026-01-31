import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui';
import { formatDateTime } from '@/utils/format';
import type { Claim } from '@/api/strategy';

interface ClaimHistoryProps {
  claims: Claim[];
  loading?: boolean;
  className?: string;
}

export function ClaimHistory({ claims, loading, className }: ClaimHistoryProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (claims.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {t('strategy.noClaims')}
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {claims.map((claim) => (
        <ClaimItem key={claim.claimId} claim={claim} />
      ))}
    </div>
  );
}

function ClaimItem({ claim }: { claim: Claim }) {
  const { t } = useTranslation();
  const statusVariant = claim.status === 'ACCEPTED' ? 'success' : claim.status === 'REJECTED' ? 'danger' : 'warning';
  const directionColor = claim.direction === 'LONG' ? 'text-green-500' : 'text-red-500';

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-gray-900 dark:text-white">{claim.witnessName}</span>
          <span className={cn('text-sm font-medium', directionColor)}>{claim.direction}</span>
          <span className="text-sm text-gray-500">
            {t('strategy.confidence')}: {(claim.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>{formatDateTime(claim.timestamp)}</span>
          {claim.reason && <span>· {claim.reason}</span>}
        </div>
      </div>
      <Badge variant={statusVariant}>{claim.status}</Badge>
    </div>
  );
}
