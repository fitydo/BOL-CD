import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ChartBarIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  CogIcon,
  Bars3Icon,
  XMarkIcon,
  BellAlertIcon,
  UserCircleIcon,
  CurrencyYenIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface LayoutProps {
  children: React.ReactNode;
}

const navigationItems = [
  { key: 'dashboard', href: '/dashboard', icon: ChartBarIcon },
  { key: 'alertReduction', href: '/reduction', icon: BellAlertIcon },
  { key: 'rules', href: '/rules', icon: ShieldCheckIcon },
  { key: 'reports', href: '/reports', icon: DocumentTextIcon },
  { key: 'pricing', href: '/pricing', icon: CurrencyYenIcon },
  { key: 'settings', href: '/settings', icon: CogIcon },
];

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  
  const navigation = navigationItems.map(item => ({
    ...item,
    name: t(`nav.${item.key}`)
  }));

  return (
    <div className="min-h-screen bg-gray-50">
      {/* モバイルサイドバー */}
      <div className={clsx(
        'fixed inset-0 z-40 lg:hidden',
        sidebarOpen ? 'block' : 'hidden'
      )}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-white">
          <div className="flex h-16 items-center justify-between px-4">
            <span className="text-xl font-bold text-indigo-600">BOL-CD</span>
            <button onClick={() => setSidebarOpen(false)}>
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md',
                    location.pathname === item.href
                      ? 'bg-indigo-100 text-indigo-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <Icon className="mr-3 h-5 w-5 flex-shrink-0" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* デスクトップサイドバー */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex min-h-0 flex-1 flex-col bg-white border-r border-gray-200">
          <div className="flex h-16 items-center justify-between px-4">
            <span className="text-xl font-bold text-indigo-600">BOL-CD Dashboard</span>
            <button
              onClick={() => navigate('/account')}
              className="p-2 rounded-lg hover:bg-gray-100"
              title={t('nav.account') || 'Account'}
            >
              <UserCircleIcon className="h-6 w-6 text-gray-600" />
            </button>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md',
                    location.pathname === item.href
                      ? 'bg-indigo-100 text-indigo-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <Icon className="mr-3 h-5 w-5 flex-shrink-0" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* メインコンテンツ */}
      <div className="lg:pl-64">
        <div className="sticky top-0 z-10 flex h-16 bg-white shadow lg:hidden">
          <button
            type="button"
            className="px-4 text-gray-500 focus:outline-none"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          <div className="flex flex-1 justify-center items-center">
            <span className="text-xl font-bold text-indigo-600">BOL-CD</span>
          </div>
        </div>
        <main className="py-6">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
