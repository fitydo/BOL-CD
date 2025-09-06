import React from 'react';
import clsx from 'clsx';

interface Alert {
  id: string;
  signature: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  count: number;
  suppressed: boolean;
  timestamp: string;
}

interface AlertsTableProps {
  alerts: Alert[];
}

export default function AlertsTable({ alerts }: AlertsTableProps) {
  // サンプルデータ（実データがない場合）
  const tableData = alerts.length > 0 ? alerts : [
    { id: '1', signature: 'SSH Brute Force', severity: 'high', count: 234, suppressed: false, timestamp: '2025-09-05T12:00:00Z' },
    { id: '2', signature: 'Port Scan Detected', severity: 'medium', count: 567, suppressed: true, timestamp: '2025-09-05T11:45:00Z' },
    { id: '3', signature: 'Failed Login Attempt', severity: 'low', count: 1234, suppressed: true, timestamp: '2025-09-05T11:30:00Z' },
    { id: '4', signature: 'Privilege Escalation', severity: 'critical', count: 12, suppressed: false, timestamp: '2025-09-05T11:15:00Z' },
    { id: '5', signature: 'Suspicious Process', severity: 'medium', count: 89, suppressed: true, timestamp: '2025-09-05T11:00:00Z' },
  ];

  const severityColors = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <div className="overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead>
          <tr>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              シグネチャ
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              重要度
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              件数
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              状態
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {tableData.map((alert) => (
            <tr key={alert.id} className="hover:bg-gray-50">
              <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {alert.signature}
              </td>
              <td className="px-3 py-4 whitespace-nowrap">
                <span className={clsx(
                  'inline-flex px-2 py-1 text-xs font-semibold rounded-full',
                  severityColors[alert.severity]
                )}>
                  {alert.severity.toUpperCase()}
                </span>
              </td>
              <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                {alert.count.toLocaleString()}
              </td>
              <td className="px-3 py-4 whitespace-nowrap">
                {alert.suppressed ? (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    抑制済み
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    アクティブ
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
