import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cn } from '@/utils/cn';

export function TabBar() {
  const location = useLocation();
  const { t } = useTranslation();

  const tabs = [
    { path: '/dashboard', label: t('nav.dashboard'), icon: '🏠' },
    { path: '/trading', label: t('nav.trading'), icon: '📊' },
    { path: '/risk', label: t('nav.risk'), icon: '⚠️' },
    { path: '/thinking', label: t('nav.thinking'), icon: '🤔' },
    { path: '/settings', label: t('nav.settings'), icon: '⚙️' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 lg:hidden z-50">
      <div className="flex items-center justify-around h-16">
        {tabs.map((tab) => (
          <Link
            key={tab.path}
            to={tab.path}
            className={cn(
              'flex flex-col items-center justify-center w-full h-full',
              location.pathname === tab.path
                ? 'text-blue-600'
                : 'text-gray-500 dark:text-gray-400'
            )}
          >
            <span className="text-xl">{tab.icon}</span>
            <span className="text-xs mt-1">{tab.label}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
