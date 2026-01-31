import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal, Button, Input, Switch } from '@/components/ui';
import type { ExchangeConfigFormData, ExchangeConfig } from '@/api/user';

interface ExchangeFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ExchangeConfigFormData) => Promise<void>;
  initialData?: ExchangeConfig | null;
}

export function ExchangeForm({ isOpen, onClose, onSubmit, initialData }: ExchangeFormProps) {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<ExchangeConfigFormData>({
    apiKey: '',
    apiSecret: '',
    testnet: initialData?.testnet ?? true,
    leverage: initialData?.leverage ?? 5,
    maxPositionPct: initialData?.maxPositionPct ?? 5,
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.apiKey.trim()) newErrors.apiKey = t('settings.apiKeyRequired');
    if (!formData.apiSecret.trim()) newErrors.apiSecret = t('settings.apiSecretRequired');
    if (formData.leverage < 1 || formData.leverage > 20) newErrors.leverage = t('settings.leverageRange');
    if (formData.maxPositionPct < 1 || formData.maxPositionPct > 30) newErrors.maxPositionPct = t('settings.positionRange');
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await onSubmit(formData);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('settings.exchangeConfigTitle')} size="md">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('settings.apiKey')}
          </label>
          <Input
            type="password"
            value={formData.apiKey}
            onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
            placeholder={t('settings.enterApiKey')}
            error={errors.apiKey}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('settings.apiSecret')}
          </label>
          <Input
            type="password"
            value={formData.apiSecret}
            onChange={(e) => setFormData({ ...formData, apiSecret: e.target.value })}
            placeholder={t('settings.enterApiSecret')}
            error={errors.apiSecret}
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-700 dark:text-gray-300">{t('settings.testnetMode')}</span>
          <Switch
            checked={formData.testnet}
            onChange={(checked) => setFormData({ ...formData, testnet: checked })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('settings.leverageMultiplier')}
          </label>
          <Input
            type="number"
            value={formData.leverage.toString()}
            onChange={(e) => setFormData({ ...formData, leverage: parseInt(e.target.value) || 1 })}
            min={1}
            max={20}
            error={errors.leverage}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('settings.maxPositionPct')}
          </label>
          <Input
            type="number"
            value={formData.maxPositionPct.toString()}
            onChange={(e) => setFormData({ ...formData, maxPositionPct: parseInt(e.target.value) || 1 })}
            min={1}
            max={30}
            error={errors.maxPositionPct}
          />
        </div>

        <div className="flex gap-3 pt-4">
          <Button variant="ghost" onClick={onClose} className="flex-1">
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSubmit} loading={loading} className="flex-1">
            {t('common.save')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
