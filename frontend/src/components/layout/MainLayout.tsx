import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { TabBar } from './TabBar';
import { useIsMobile } from '@/hooks/useMediaQuery';

export function MainLayout() {
  const isMobile = useIsMobile();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {!isMobile && <Navbar />}
      <main className={cn('max-w-7xl mx-auto px-4 py-6', isMobile && 'pb-20')}>
        <Outlet />
      </main>
      {isMobile && <TabBar />}
    </div>
  );
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}
