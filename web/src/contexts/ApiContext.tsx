import React, { createContext, useContext, useState } from 'react';
import axios, { AxiosInstance } from 'axios';

interface ApiContextType {
  client: AxiosInstance;
  fetchMetrics: () => Promise<any>;
  fetchLatestReport: () => Promise<any>;
  fetchRules: () => Promise<any>;
  createRule: (rule: any) => Promise<any>;
  updateRule: (name: string, rule: any) => Promise<any>;
  deleteRule: (name: string) => Promise<any>;
  recomputeEdges: (params: any) => Promise<any>;
  fetchGraph: (format?: string) => Promise<any>;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

export function ApiProvider({ children }: { children: React.ReactNode }) {
  // Use Vite env vars with safe fallbacks to avoid "process is not defined" in browser
  const viteEnv: any = (import.meta as any)?.env || {};
  const baseUrl: string = viteEnv.VITE_API_URL || 'http://localhost:8080';
  const defaultApiKey: string = viteEnv.VITE_API_KEY || 'viewer:default-key';

  const [apiKey] = useState(() => {
    return localStorage.getItem('bolcd_api_key') || defaultApiKey;
  });

  const client = axios.create({
    baseURL: baseUrl,
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json',
    },
  });

  // エラーハンドリング
  client.interceptors.response.use(
    response => response,
    error => {
      if (error.response?.status === 429) {
        console.error('Rate limit exceeded');
      } else if (error.response?.status === 403) {
        console.error('Permission denied');
      }
      return Promise.reject(error);
    }
  );

  const api: ApiContextType = {
    client,

    fetchMetrics: async () => {
      const response = await client.get('/metrics', { responseType: 'text' });
      // Prometheusフォーマットをパース
      const text: string = typeof response.data === 'string' ? response.data : String(response.data);
      const metrics: any = {};
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('#') || !line.trim()) continue;
        const match = line.match(/^(\w+)(?:\{[^}]*\})?\s+([\d.]+)/);
        if (match) {
          metrics[match[1]] = parseFloat(match[2]);
        }
      }
      return metrics;
    },

    fetchLatestReport: async () => {
      try {
        const response = await client.get('/api/reports/daily/latest');
        return response.data;
      } catch (error) {
        console.error('Failed to fetch latest report:', error);
        // モックデータを返す（APIが利用できない場合）
        return {
          reduction_by_count: 0.585,
          suppressed_count: 5850,
          false_suppression_rate: 0.0,
          total_events: 10000,
          top_suppressed: [
            { signature: 'Info Log', count: 2000 },
            { signature: 'Debug Message', count: 1500 },
            { signature: 'Warning Alert', count: 1000 }
          ],
          history: [
            { date: '2025-09-01', reduction: 45, target: 50 },
            { date: '2025-09-02', reduction: 48, target: 50 },
            { date: '2025-09-03', reduction: 52, target: 50 },
            { date: '2025-09-04', reduction: 55, target: 50 },
            { date: '2025-09-05', reduction: 58.5, target: 50 }
          ],
          recent_alerts: []
        };
      }
    },

    fetchRules: async () => {
      try {
        const response = await client.get('/api/rules');
        return response.data;
      } catch (error) {
        console.error('Failed to fetch rules:', error);
        // モックデータ
        return {
          rules: [
            { name: 'ssh_detection', enabled: true, severity: 'high', description: 'SSH brute force detection' },
            { name: 'port_scan', enabled: true, severity: 'medium', description: 'Port scanning detection' },
            { name: 'failed_login', enabled: false, severity: 'low', description: 'Failed login attempts' }
          ]
        };
      }
    },

    createRule: async (rule) => {
      const response = await client.post('/api/rules', rule);
      return response.data;
    },

    updateRule: async (name, rule) => {
      const response = await client.put(`/api/rules/${name}`, rule);
      return response.data;
    },

    deleteRule: async (name) => {
      const response = await client.delete(`/api/rules/${name}`);
      return response.data;
    },

    recomputeEdges: async (params) => {
      const response = await client.post('/api/edges/recompute', params);
      return response.data;
    },

    fetchGraph: async (format = 'json') => {
      const response = await client.get('/api/graph', { params: { format } });
      return response.data;
    },
  };

  return (
    <ApiContext.Provider value={api}>
      {children}
    </ApiContext.Provider>
  );
}

export function useApi() {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within ApiProvider');
  }
  return context;
}
