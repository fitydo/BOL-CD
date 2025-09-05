import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  KeyIcon, 
  ServerIcon, 
  BellIcon, 
  ShieldCheckIcon,
  GlobeAltIcon,
  CogIcon,
  CheckIcon
} from '@heroicons/react/24/outline';

export default function Settings() {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState('general');
  const [saved, setSaved] = useState(false);
  
  const [settings, setSettings] = useState({
    organizationName: 'Acme Corporation',
    timezone: 'Asia/Tokyo',
    language: 'ja',
    apiUrl: 'http://localhost:8080',
    apiKey: 'viewer:default-key',
    emailNotifications: true,
    mfaEnabled: false,
  });

  const handleSave = () => {
    localStorage.setItem('bolcd_settings', JSON.stringify(settings));
    // 言語設定を即座に反映
    if (settings.language !== i18n.language) {
      i18n.changeLanguage(settings.language);
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const tabs = [
    { id: 'general', name: t('settings.tabs.general'), icon: CogIcon },
    { id: 'api', name: t('settings.tabs.api'), icon: ServerIcon },
    { id: 'siem', name: t('settings.tabs.siem'), icon: GlobeAltIcon },
    { id: 'notifications', name: t('settings.tabs.notifications'), icon: BellIcon },
    { id: 'security', name: t('settings.tabs.security'), icon: ShieldCheckIcon },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t('settings.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t('settings.subtitle')}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center
                    ${activeTab === tab.id
                      ? 'border-indigo-500 text-indigo-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('settings.general.organizationName')}
                </label>
                <input
                  type="text"
                  value={settings.organizationName}
                  onChange={(e) => setSettings({...settings, organizationName: e.target.value})}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('settings.general.timezone')}
                </label>
                <select
                  value={settings.timezone}
                  onChange={(e) => setSettings({...settings, timezone: e.target.value})}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                >
                  <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York (EST)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('settings.general.language')}
                </label>
                <select
                  value={settings.language}
                  onChange={(e) => {
                    setSettings({...settings, language: e.target.value});
                    // 即座に言語を切り替え
                    i18n.changeLanguage(e.target.value);
                  }}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                >
                  <option value="ja">🇯🇵 日本語</option>
                  <option value="en">🇺🇸 English</option>
                  <option value="zh">🇨🇳 中文 (Coming soon)</option>
                  <option value="ko">🇰🇷 한국어 (Coming soon)</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  {t('settings.general.languageHelp', 'UIの表示言語を変更します')}
                </p>
              </div>
            </div>
          )}

          {activeTab === 'api' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  API URL
                </label>
                <input
                  type="text"
                  value={settings.apiUrl}
                  onChange={(e) => setSettings({...settings, apiUrl: e.target.value})}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  APIキー
                </label>
                <div className="mt-1 flex rounded-md shadow-sm">
                  <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 sm:text-sm">
                    <KeyIcon className="h-4 w-4" />
                  </span>
                  <input
                    type="password"
                    value={settings.apiKey}
                    onChange={(e) => setSettings({...settings, apiKey: e.target.value})}
                    className="flex-1 block w-full rounded-none rounded-r-md border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'siem' && (
            <div className="space-y-6">
              <div className="border rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">SIEM連携設定</h3>
                <div className="space-y-4">
                  <div className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    <label>Splunk連携を有効化</label>
                  </div>
                  <div className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    <label>Azure Sentinel連携を有効化</label>
                  </div>
                  <div className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    <label>OpenSearch連携を有効化</label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-900">メール通知</h3>
                  <p className="text-sm text-gray-500">重要なアラートをメールで受信</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.emailNotifications}
                    onChange={(e) => setSettings({...settings, emailNotifications: e.target.checked})}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-900">多要素認証（MFA）</h3>
                  <p className="text-sm text-gray-500">ログイン時の追加認証</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.mfaEnabled}
                    onChange={(e) => setSettings({...settings, mfaEnabled: e.target.checked})}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
            </div>
          )}
        </div>

        <div className="bg-gray-50 px-6 py-3 flex justify-end">
          <button
            onClick={handleSave}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {saved && <CheckIcon className="h-5 w-5 mr-2" />}
            {saved ? '保存しました' : '設定を保存'}
          </button>
        </div>
      </div>
    </div>
  );
}