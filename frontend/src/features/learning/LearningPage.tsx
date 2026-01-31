import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, Button, Tabs, TabPanel } from '@/components/ui';
import { ReportOverview, SuggestionList, WitnessRanking } from '@/components/learning';
import { useLearningStore } from '@/stores/learningStore';
import { learningApi } from '@/api/learning';
import { useMediaQuery } from '@/hooks/useMediaQuery';

type ReportPeriod = '7d' | '30d' | '90d';

export function LearningPage() {
  const { t } = useTranslation();
  const isMobile = useMediaQuery('(max-width: 1023px)');
  const [isLoading, setIsLoading] = useState(true);
  const [period, setPeriod] = useState<ReportPeriod>('7d');
  const [activeTab, setActiveTab] = useState('suggestions');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [batchLoading, setBatchLoading] = useState(false);

  const { report, suggestions, witnessRanking, setReport, setSuggestions, setWitnessRanking, updateSuggestion } = useLearningStore();

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [reportRes, suggestionsRes, rankingRes] = await Promise.allSettled([
          learningApi.getReport(period),
          learningApi.getSuggestions(true),
          learningApi.getWitnessRanking(),
        ]);
        if (reportRes.status === 'fulfilled') setReport(reportRes.value);
        if (suggestionsRes.status === 'fulfilled') setSuggestions(suggestionsRes.value.suggestions);
        if (rankingRes.status === 'fulfilled') setWitnessRanking(rankingRes.value);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [period, setReport, setSuggestions, setWitnessRanking]);

  const handleSelect = (id: string, selected: boolean) => {
    setSelectedIds((prev) => selected ? [...prev, id] : prev.filter((i) => i !== id));
  };

  const handleApprove = async (id: string) => {
    setActionLoading(id);
    try {
      await learningApi.approveSuggestions([id], true);
      updateSuggestion(id, 'APPROVED');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: string) => {
    setActionLoading(id);
    try {
      await learningApi.approveSuggestions([id], false);
      updateSuggestion(id, 'REJECTED');
    } finally {
      setActionLoading(null);
    }
  };

  const handleBatchApprove = async (approved: boolean) => {
    if (selectedIds.length === 0) return;
    setBatchLoading(true);
    try {
      await learningApi.approveSuggestions(selectedIds, approved);
      selectedIds.forEach((id) => updateSuggestion(id, approved ? 'APPROVED' : 'REJECTED'));
      setSelectedIds([]);
    } finally {
      setBatchLoading(false);
    }
  };

  const pendingSuggestions = suggestions.filter((s) => s.status === 'PENDING');

  const tabs = [
    { id: 'suggestions', label: `${t('learning.suggestions')} (${pendingSuggestions.length})` },
    { id: 'ranking', label: t('learning.witnessRanking') },
  ];

  const periodLabels: Record<ReportPeriod, string> = {
    '7d': t('learning.days7'),
    '30d': t('learning.days30'),
    '90d': t('learning.days90'),
  };

  if (isMobile) {
    return (
      <div className="space-y-4 pb-20">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t('learning.title')}</h1>
          <select value={period} onChange={(e) => setPeriod(e.target.value as ReportPeriod)} className="px-2 py-1 text-sm border rounded dark:bg-gray-800 dark:border-gray-700">
            <option value="7d">{periodLabels['7d']}</option>
            <option value="30d">{periodLabels['30d']}</option>
            <option value="90d">{periodLabels['90d']}</option>
          </select>
        </div>
        <ReportOverview report={report} loading={isLoading} />
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
        <TabPanel isActive={activeTab === 'suggestions'}>
          {selectedIds.length > 0 && (
            <div className="flex gap-2 mb-4">
              <Button size="sm" variant="primary" onClick={() => handleBatchApprove(true)} loading={batchLoading}>{t('learning.batchApprove')} ({selectedIds.length})</Button>
              <Button size="sm" variant="ghost" onClick={() => handleBatchApprove(false)} loading={batchLoading}>{t('learning.batchReject')}</Button>
            </div>
          )}
          <SuggestionList suggestions={pendingSuggestions} loading={isLoading} selectedIds={selectedIds} onSelect={handleSelect} onApprove={handleApprove} onReject={handleReject} actionLoading={actionLoading} />
        </TabPanel>
        <TabPanel isActive={activeTab === 'ranking'}>
          <WitnessRanking ranking={witnessRanking} loading={isLoading} />
        </TabPanel>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('learning.title')}</h1>
        <div className="flex gap-2">
          {(['7d', '30d', '90d'] as const).map((p) => (
            <button key={p} onClick={() => setPeriod(p)} className={`px-3 py-1 text-sm rounded ${period === p ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
              {periodLabels[p]}
            </button>
          ))}
        </div>
      </div>
      <ReportOverview report={report} loading={isLoading} />
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{t('learning.suggestions')}</CardTitle>
                {selectedIds.length > 0 && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="primary" onClick={() => handleBatchApprove(true)} loading={batchLoading}>{t('learning.batchApprove')} ({selectedIds.length})</Button>
                    <Button size="sm" variant="ghost" onClick={() => handleBatchApprove(false)} loading={batchLoading}>{t('learning.batchReject')}</Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <SuggestionList suggestions={pendingSuggestions} loading={isLoading} selectedIds={selectedIds} onSelect={handleSelect} onApprove={handleApprove} onReject={handleReject} actionLoading={actionLoading} />
            </CardContent>
          </Card>
        </div>
        <Card>
          <CardHeader><CardTitle>{t('learning.witnessRanking')}</CardTitle></CardHeader>
          <CardContent><WitnessRanking ranking={witnessRanking} loading={isLoading} /></CardContent>
        </Card>
      </div>
    </div>
  );
}
