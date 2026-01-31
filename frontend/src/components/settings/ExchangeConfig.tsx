import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Badge, ConfirmDialog } from '@/components/ui';
import { formatDateTime } from '@/utils/format';
import type { ExchangeConfig as ExchangeConfigType } from '@/api/user';

interface ExchangeConfigProps {
  config: ExchangeConfigType | null;
  loading?: boolean;
  onEdit: () => void;
  onVerify: () => Promise<void>;
  onDelete: () => Promise<void>;
}

export function ExchangeConfig({ config, loading, onEdit, onVerify, onDelete }: ExchangeConfigProps) {
  const { t } = useTranslation();
  const [verifying, setVerifying] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      await onVerify();
    } finally {
      setVerifying(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete();
      setShowDeleteConfirm(false);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 mb-4">{t('settings.noExchangeConfig')}</p>
        <Button onClick={onEdit}>{t('settings.addConfig')}</Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.exchange')}</span>
        <span className="font-medium text-gray-900 dark:text-white">{config.exchange}</span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.status')}</span>
        <Badge variant={config.isValid ? 'success' : 'danger'}>
          {config.isValid ? `🟢 ${t('settings.verified')}` : `🔴 ${t('settings.unverified')}`}
        </Badge>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.apiKey')}</span>
        <span className="font-mono text-sm text-gray-900 dark:text-white">
          {config.apiKeyMasked}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.mode')}</span>
        <Badge variant={config.testnet ? 'warning' : 'info'}>
          {config.testnet ? t('settings.testnet') : t('settings.mainnet')}
        </Badge>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.leverage')}</span>
        <span className="text-gray-900 dark:text-white">{config.leverage}x</span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.maxPosition')}</span>
        <span className="text-gray-900 dark:text-white">{config.maxPositionPct}%</span>
      </div>

      {config.lastVerifiedAt && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">{t('settings.lastVerified')}</span>
          <span className="text-sm text-gray-900 dark:text-white">
            {formatDateTime(config.lastVerifiedAt)}
          </span>
        </div>
      )}

      <div className="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button variant="outline" size="sm" onClick={handleVerify} loading={verifying}>
          {t('settings.reverify')}
        </Button>
        <Button variant="outline" size="sm" onClick={onEdit}>
          {t('settings.modify')}
        </Button>
        <Button variant="danger" size="sm" onClick={() => setShowDeleteConfirm(true)}>
          {t('common.delete')}
        </Button>
      </div>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={handleDelete}
        title={t('settings.deleteConfig')}
        message={t('settings.deleteConfigConfirm')}
        confirmText={t('common.delete')}
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}
