import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showDemoAccounts, setShowDemoAccounts] = useState(true);
  
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    fullName: ''
  });
  
  const demoAccounts = [
    { email: 'admin@demo.com', password: 'admin123', role: 'Administrator', color: 'bg-purple-100 text-purple-800' },
    { email: 'analyst@demo.com', password: 'analyst123', role: 'Security Analyst', color: 'bg-blue-100 text-blue-800' },
    { email: 'user@demo.com', password: 'user123', role: 'Regular User', color: 'bg-gray-100 text-gray-800' }
  ];
  
  const handleDemoLogin = (email: string, password: string) => {
    setFormData({ ...formData, email, password });
    setShowDemoAccounts(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Mock authentication for demo
      const demoCredentials = [
        { email: 'admin@demo.com', password: 'admin123' },
        { email: 'analyst@demo.com', password: 'analyst123' },
        { email: 'user@demo.com', password: 'user123' }
      ];
      
      const isValidLogin = demoCredentials.some(
        cred => cred.email === formData.email && cred.password === formData.password
      );
      
      if (isLogin) {
        if (isValidLogin) {
          // Mock successful login
          const mockToken = btoa(JSON.stringify({
            email: formData.email,
            role: formData.email.includes('admin') ? 'admin' : 
                  formData.email.includes('analyst') ? 'analyst' : 'user',
            exp: Date.now() + 3600000
          }));
          
          localStorage.setItem('access_token', mockToken);
          localStorage.setItem('refresh_token', mockToken);
          localStorage.setItem('user_email', formData.email);
          
          // Redirect to dashboard
          navigate('/');
        } else {
          setError(t('auth.error.generic') || 'Invalid credentials');
        }
      } else {
        // Mock registration
        const mockToken = btoa(JSON.stringify({
          email: formData.email,
          username: formData.username,
          role: 'user',
          exp: Date.now() + 3600000
        }));
        
        localStorage.setItem('access_token', mockToken);
        localStorage.setItem('refresh_token', mockToken);
        localStorage.setItem('user_email', formData.email);
        
        navigate('/');
      }
    } catch (err: any) {
      setError(t('auth.error.generic'));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setLoading(true);
    
    // Google OAuth flow
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setError(t('auth.error.googleNotConfigured'));
      setLoading(false);
      return;
    }

    // Initialize Google Sign-In
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      // @ts-ignore
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response: any) => {
          try {
            const res = await axios.post(
              `http://localhost:8080/api/auth/google`,
              { id_token: response.credential }
            );
            
            localStorage.setItem('access_token', res.data.access_token);
            localStorage.setItem('refresh_token', res.data.refresh_token);
            navigate('/');
          } catch (err: any) {
            setError(err.response?.data?.detail || t('auth.error.googleFailed'));
          } finally {
            setLoading(false);
          }
        }
      });
      
      // @ts-ignore
      google.accounts.id.prompt();
    };
    document.body.appendChild(script);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 to-blue-100">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-2xl">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {isLogin ? t('auth.login.title') : t('auth.signup.title')}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {isLogin ? t('auth.login.subtitle') : t('auth.signup.subtitle')}
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                {t('auth.field.email')}
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            
            {!isLogin && (
              <>
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                    {t('auth.field.username')}
                  </label>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    autoComplete="username"
                    required
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium text-gray-700">
                    {t('auth.field.fullName')}
                  </label>
                  <input
                    id="fullName"
                    name="fullName"
                    type="text"
                    autoComplete="name"
                    value={formData.fullName}
                    onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </>
            )}
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                {t('auth.field.password')}
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
                required
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            
            {!isLogin && (
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                  {t('auth.field.confirmPassword')}
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            )}
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {loading ? t('auth.loading') : (isLogin ? t('auth.login.submit') : t('auth.signup.submit'))}
            </button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">{t('auth.or')}</span>
            </div>
          </div>

          <div>
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              {t('auth.googleSignIn')}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm text-indigo-600 hover:text-indigo-500"
            >
              {isLogin ? t('auth.switchToSignup') : t('auth.switchToLogin')}
            </button>
          </div>
        </form>
        
        {/* Demo Accounts Section */}
        {isLogin && showDemoAccounts && (
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <h3 className="text-sm font-semibold text-yellow-800 mb-3">
              {t('auth.demoAccounts', 'Demo Accounts for Testing')}
            </h3>
            <div className="space-y-2">
              {demoAccounts.map((account) => (
                <button
                  key={account.email}
                  onClick={() => handleDemoLogin(account.email, account.password)}
                  className="w-full text-left p-3 bg-white rounded-lg border border-yellow-200 hover:bg-yellow-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">{account.email}</div>
                      <div className="text-xs text-gray-500">Password: {account.password}</div>
                    </div>
                    <span className={`px-2 py-1 text-xs rounded-full ${account.color}`}>
                      {account.role}
                    </span>
                  </div>
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-yellow-700">
              {t('auth.demoNote', 'Click any account to auto-fill credentials')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
