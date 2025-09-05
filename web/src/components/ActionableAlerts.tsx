import React, { useState, useEffect } from 'react';
import { ExclamationTriangleIcon, BellAlertIcon, ArrowRightIcon } from '@heroicons/react/24/outline';

interface Alert {
  id: string;
  severity: 'critical' | 'high';
  signature: string;
  entity_id: string;
  timestamp: string;
  suppression_score: number;
}

export default function ActionableAlerts() {
  const [criticalAlerts, setCriticalAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 実際のAPIから取得（現在はモックデータ）
    const mockAlerts: Alert[] = [
      {
        id: '1',
        severity: 'critical',
        signature: 'Privilege Escalation Detected',
        entity_id: 'prod-db-01',
        timestamp: new Date().toISOString(),
        suppression_score: 0.12
      },
      {
        id: '2',
        severity: 'critical',
        signature: 'Ransomware Activity',
        entity_id: 'fin-app-02',
        timestamp: new Date().toISOString(),
        suppression_score: 0.08
      },
      {
        id: '3',
        severity: 'high',
        signature: 'Data Exfiltration Attempt',
        entity_id: 'hr-server',
        timestamp: new Date().toISOString(),
        suppression_score: 0.18
      }
    ];

    setCriticalAlerts(mockAlerts);
    setLoading(false);
  }, []);

  if (loading) {
    return <div className="animate-pulse bg-gray-100 h-32 rounded-lg"></div>;
  }

  if (criticalAlerts.length === 0) {
    return (
      <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded-lg">
        <div className="flex">
          <BellAlertIcon className="h-5 w-5 text-green-400" />
          <div className="ml-3">
            <p className="text-sm text-green-700">
              現在、緊急対応が必要なアラートはありません
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium text-gray-900 flex items-center">
        <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
        対応が必要なアラート（{criticalAlerts.length}件）
      </h2>

      <div className="space-y-3">
        {criticalAlerts.map((alert) => (
          <div
            key={alert.id}
            className={`
              border-l-4 p-4 rounded-lg
              ${alert.severity === 'critical' 
                ? 'bg-red-50 border-red-400' 
                : 'bg-orange-50 border-orange-400'}
            `}
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center">
                  <span className={`
                    inline-flex px-2 py-1 text-xs font-semibold rounded-full mr-2
                    ${alert.severity === 'critical'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-orange-100 text-orange-800'}
                  `}>
                    {alert.severity.toUpperCase()}
                  </span>
                  <h3 className="text-sm font-medium text-gray-900">
                    {alert.signature}
                  </h3>
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  対象: {alert.entity_id} | 
                  抑制スコア: {alert.suppression_score.toFixed(2)} |
                  {new Date(alert.timestamp).toLocaleTimeString('ja-JP')}
                </p>
              </div>
              <button className="text-sm font-medium text-indigo-600 hover:text-indigo-500 flex items-center">
                詳細
                <ArrowRightIcon className="ml-1 h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex gap-3">
        <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700">
          SOCダッシュボードを開く
        </button>
        <button className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
          SIEMで確認
        </button>
      </div>
    </div>
  );
}
