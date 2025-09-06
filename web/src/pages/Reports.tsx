import React, { useState, useEffect } from 'react';
import { useApi } from '../contexts/ApiContext';
import { CalendarIcon, DocumentArrowDownIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

export default function Reports() {
  const { fetchLatestReport } = useApi();
  const [selectedPeriod, setSelectedPeriod] = useState('daily');
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, [selectedPeriod]);

  const loadReports = async () => {
    setLoading(true);
    try {
      // 最新レポートを取得（実際にはperiodに応じて変更）
      const latest = await fetchLatestReport();
      
      // サンプルの履歴データ
      const mockReports = [
        {
          id: '1',
          date: '2025-09-05',
          type: 'daily',
          reduction_rate: 0.585,
          events_processed: 10000,
          alerts_suppressed: 5850,
          status: 'completed'
        },
        {
          id: '2',
          date: '2025-09-04',
          type: 'daily',
          reduction_rate: 0.55,
          events_processed: 9500,
          alerts_suppressed: 5225,
          status: 'completed'
        },
        {
          id: '3',
          date: '2025-09-03',
          type: 'daily',
          reduction_rate: 0.52,
          events_processed: 9200,
          alerts_suppressed: 4784,
          status: 'completed'
        },
        {
          id: '4',
          date: '2025-09-02',
          type: 'daily',
          reduction_rate: 0.48,
          events_processed: 8800,
          alerts_suppressed: 4224,
          status: 'completed'
        },
        {
          id: '5',
          date: '2025-09-01',
          type: 'daily',
          reduction_rate: 0.45,
          events_processed: 8500,
          alerts_suppressed: 3825,
          status: 'completed'
        }
      ];
      
      setReports(mockReports);
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (format: 'csv' | 'json' | 'pdf') => {
    // エクスポート処理（実装例）
    console.log(`Exporting as ${format}...`);
    alert(`レポートを${format.toUpperCase()}形式でエクスポートします`);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">レポート</h1>
          <p className="mt-1 text-sm text-gray-500">
            日次・週次レポートの閲覧とエクスポート
          </p>
        </div>
        
        <div className="flex gap-2">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="daily">日次</option>
            <option value="weekly">週次</option>
            <option value="monthly">月次</option>
          </select>
        </div>
      </div>

      {/* サマリーカード */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              平均削減率
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-indigo-600">
              52.0%
            </dd>
            <p className="mt-2 text-sm text-gray-500">
              過去7日間
            </p>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              総削減アラート数
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              28,908
            </dd>
            <p className="mt-2 text-sm text-gray-500">
              過去7日間
            </p>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              処理イベント数
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              55,000
            </dd>
            <p className="mt-2 text-sm text-gray-500">
              過去7日間
            </p>
          </div>
        </div>
      </div>

      {/* レポート一覧 */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-gray-900">レポート履歴</h2>
            <div className="flex gap-2">
              <button
                onClick={() => handleExport('csv')}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
                CSV
              </button>
              <button
                onClick={() => handleExport('json')}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
                JSON
              </button>
              <button
                onClick={() => handleExport('pdf')}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
                PDF
              </button>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            </div>
          ) : (
            <div className="overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      日付
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      タイプ
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      削減率
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      処理イベント
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      削減アラート
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状態
                    </th>
                    <th className="relative px-6 py-3">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {reports.map((report) => (
                    <tr key={report.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <CalendarIcon className="h-4 w-4 mr-2 text-gray-400" />
                          {format(new Date(report.date), 'yyyy/MM/dd')}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                          {report.type === 'daily' ? '日次' : report.type === 'weekly' ? '週次' : '月次'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <ChartBarIcon className="h-4 w-4 mr-2 text-indigo-500" />
                          <span className="font-medium">{(report.reduction_rate * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {report.events_processed.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {report.alerts_suppressed.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          完了
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button className="text-indigo-600 hover:text-indigo-900">
                          詳細
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* グラフセクション */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">削減率トレンド</h2>
        <div className="h-64 bg-gray-50 rounded flex items-center justify-center text-gray-500">
          グラフコンポーネント（Rechartsを使用して実装）
        </div>
      </div>
    </div>
  );
}