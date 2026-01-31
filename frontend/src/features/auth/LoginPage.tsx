import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/hooks/useAuth';
import { Button, Input, Card, CardContent, toast } from '@/components/ui';

export function LoginPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  const toggleLanguage = () => {
    const newLang = i18n.language === 'zh' ? 'en' : 'zh';
    i18n.changeLanguage(newLang);
    localStorage.setItem('language', newLang);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      await login(email, password);
      toast.success(t('common.success'));
      navigate(from, { replace: true });
    } catch {
      toast.error(error || t('auth.loginFailed'));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex justify-end mb-2">
            <button onClick={toggleLanguage} className="px-2 py-1 text-sm font-medium text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded">
              {i18n.language === 'zh' ? 'EN' : '中文'}
            </button>
          </div>
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">BTC Trading System</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">{t('auth.loginTitle')}</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input id="email" type="email" label={t('auth.email')} placeholder="your@email.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Input id="password" type="password" label={t('auth.password')} placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" isLoading={isLoading}>{t('auth.login')}</Button>
          </form>
          <p className="text-center text-sm text-gray-600 dark:text-gray-400 mt-4">
            {t('auth.noAccount')} <Link to="/register" className="text-blue-600 hover:underline">{t('auth.register')}</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
