import { useState } from 'react';
import { Button, ConfirmDialog, Input } from '@/components/ui';

interface SystemActionsProps {
  onForceLock: (reason: string) => Promise<void>;
  onForceUnlock: () => Promise<void>;
}

export function SystemActions({ onForceLock, onForceUnlock }: SystemActionsProps) {
  const [showLockConfirm, setShowLockConfirm] = useState(false);
  const [showUnlockConfirm, setShowUnlockConfirm] = useState(false);
  const [lockReason, setLockReason] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLock = async () => {
    if (!lockReason.trim()) return;
    setLoading(true);
    try {
      await onForceLock(lockReason);
      setShowLockConfirm(false);
      setLockReason('');
    } finally {
      setLoading(false);
    }
  };

  const handleUnlock = async () => {
    setLoading(true);
    try {
      await onForceUnlock();
      setShowUnlockConfirm(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="font-medium text-gray-900 dark:text-white">系统操作</h3>
      <div className="flex gap-3">
        <Button variant="danger" onClick={() => setShowLockConfirm(true)}>
          强制锁定系统
        </Button>
        <Button variant="outline" onClick={() => setShowUnlockConfirm(true)}>
          解除系统锁定
        </Button>
      </div>

      <ConfirmDialog
        isOpen={showLockConfirm}
        onClose={() => setShowLockConfirm(false)}
        onConfirm={handleLock}
        title="强制锁定系统"
        message=""
        confirmText="锁定"
        variant="danger"
        loading={loading}
      >
        <div className="mb-4">
          <p className="text-gray-600 dark:text-gray-300 mb-3">
            确定要强制锁定系统吗？锁定后所有交易将被暂停。
          </p>
          <Input
            placeholder="请输入锁定原因"
            value={lockReason}
            onChange={(e) => setLockReason(e.target.value)}
          />
        </div>
      </ConfirmDialog>

      <ConfirmDialog
        isOpen={showUnlockConfirm}
        onClose={() => setShowUnlockConfirm(false)}
        onConfirm={handleUnlock}
        title="解除系统锁定"
        message="确定要解除系统锁定吗？解除后系统将恢复正常交易。"
        confirmText="解除锁定"
        loading={loading}
      />
    </div>
  );
}
