import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  UserCircleIcon,
  EnvelopeIcon,
  KeyIcon,
  TrashIcon,
  ArrowRightOnRectangleIcon
} from '@heroicons/react/24/outline';

interface UserProfile {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  avatar_url?: string;
  auth_provider: string;
  role: string;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

export default function Account() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [passwordModal, setPasswordModal] = useState(false);
  const [deleteModal, setDeleteModal] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  const [profileForm, setProfileForm] = useState({
    username: '',
    full_name: '',
    avatar_url: ''
  });
  
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  const apiUrl = 'http://localhost:8080';

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const email = localStorage.getItem('user_email');
      if (!token) {
        navigate('/login');
        return;
      }

      // Mock user profile
      const mockUser: UserProfile = {
        id: 1,
        email: email || 'admin@demo.com',
        username: email?.split('@')[0] || 'admin',
        full_name: email?.includes('admin') ? 'Demo Administrator' : 
                   email?.includes('analyst') ? 'Security Analyst' : 'Demo User',
        avatar_url: `https://ui-avatars.com/api/?name=${email?.split('@')[0]}&background=6366f1&color=fff`,
        auth_provider: 'local',
        role: email?.includes('admin') ? 'admin' : 
              email?.includes('analyst') ? 'analyst' : 'user',
        is_verified: true,
        created_at: new Date().toISOString(),
        last_login: new Date().toISOString()
      };

      setUser(mockUser);
      setProfileForm({
        username: mockUser.username,
        full_name: mockUser.full_name || '',
        avatar_url: mockUser.avatar_url || ''
      });
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async () => {
    try {
      // Mock update
      if (user) {
        setUser({
          ...user,
          ...profileForm
        });
        setEditing(false);
        setMessage({ type: 'success', text: t('account.updateSuccess') });
        setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: t('account.updateError') });
    }
  };

  const handleChangePassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMessage({ type: 'error', text: t('account.passwordMismatch') });
      return;
    }

    // Mock password change
    setPasswordModal(false);
    setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    setMessage({ type: 'success', text: t('account.passwordChanged') });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleDeleteAccount = async () => {
    // Mock delete
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_email');
    navigate('/login');
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-900">{t('account.title')}</h1>
        </div>

        {message.text && (
          <div className={`mx-6 mt-4 p-4 rounded ${
            message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
            {message.text}
          </div>
        )}

        <div className="p-6">
          {/* Profile Section */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">{t('account.profile')}</h2>
              <button
                onClick={() => editing ? handleUpdateProfile() : setEditing(true)}
                className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
              >
                {editing ? t('account.save') : t('account.edit')}
              </button>
            </div>

            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt={user.username} className="w-20 h-20 rounded-full" />
                ) : (
                  <UserCircleIcon className="w-20 h-20 text-gray-400" />
                )}
                <div>
                  <p className="text-sm text-gray-500">{t('account.memberSince')}</p>
                  <p className="font-medium">{new Date(user.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">{t('account.email')}</label>
                  <div className="mt-1 flex items-center">
                    <EnvelopeIcon className="w-5 h-5 text-gray-400 mr-2" />
                    <span className="text-gray-900">{user.email}</span>
                    {user.is_verified && (
                      <span className="ml-2 px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                        {t('account.verified')}
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">{t('account.username')}</label>
                  {editing ? (
                    <input
                      type="text"
                      value={profileForm.username}
                      onChange={(e) => setProfileForm({...profileForm, username: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  ) : (
                    <p className="mt-1 text-gray-900">@{user.username}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">{t('account.fullName')}</label>
                  {editing ? (
                    <input
                      type="text"
                      value={profileForm.full_name}
                      onChange={(e) => setProfileForm({...profileForm, full_name: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  ) : (
                    <p className="mt-1 text-gray-900">{user.full_name || '-'}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">{t('account.authProvider')}</label>
                  <p className="mt-1 text-gray-900 capitalize">{user.auth_provider}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">{t('account.role')}</label>
                  <p className="mt-1">
                    <span className={`px-2 py-1 text-xs rounded ${
                      user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {user.role}
                    </span>
                  </p>
                </div>

                {user.last_login && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">{t('account.lastLogin')}</label>
                    <p className="mt-1 text-gray-900">
                      {new Date(user.last_login).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Security Section */}
          <div className="border-t pt-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{t('account.security')}</h2>
            
            <div className="space-y-4">
              {user.auth_provider === 'local' && (
                <button
                  onClick={() => setPasswordModal(true)}
                  className="flex items-center px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  <KeyIcon className="w-5 h-5 mr-2" />
                  {t('account.changePassword')}
                </button>
              )}

              <button
                onClick={handleLogout}
                className="flex items-center px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                <ArrowRightOnRectangleIcon className="w-5 h-5 mr-2" />
                {t('account.logout')}
              </button>

              <button
                onClick={() => setDeleteModal(true)}
                className="flex items-center px-4 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50"
              >
                <TrashIcon className="w-5 h-5 mr-2" />
                {t('account.deleteAccount')}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Password Change Modal */}
      {passwordModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">{t('account.changePassword')}</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('account.currentPassword')}
                </label>
                <input
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm({...passwordForm, current_password: e.target.value})}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('account.newPassword')}
                </label>
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({...passwordForm, new_password: e.target.value})}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('account.confirmNewPassword')}
                </label>
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({...passwordForm, confirm_password: e.target.value})}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setPasswordModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleChangePassword}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                {t('common.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Account Modal */}
      {deleteModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4 text-red-600">{t('account.deleteAccountConfirm')}</h3>
            <p className="text-gray-600 mb-6">{t('account.deleteAccountWarning')}</p>
            
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setDeleteModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleDeleteAccount}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                {t('account.deleteConfirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
