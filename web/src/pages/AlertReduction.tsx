import React, { useState, useEffect } from 'react';
import { useApi } from '../contexts/ApiContext';
import { PlayIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

export default function AlertReduction() {
  const { recomputeEdges, fetchLatestReport } = useApi();
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [config, setConfig] = useState({
    targetReduction: 0.6,
    epsilon: 0.02,
    fdrQ: 0.01,
    eventsPath: '/data/events.jsonl',
  });

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    try {
      const data = await fetchLatestReport();
      setReport(data);
    } catch (error) {
      console.error('Failed to load report:', error);
    }
  };

  const handleOptimize = async () => {
    setLoading(true);
    try {
      await recomputeEdges({
        events_path: config.eventsPath,
        epsilon: config.epsilon,
        fdr_q: config.fdrQ,
      });
      await loadReport();
      alert('最適化が完了しました');
    } catch (error) {
      console.error('Optimization failed:', error);
      alert('最適化に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">アラート削減</h1>
        <p className="mt-1 text-sm text-gray-500">
          機械学習による自動削減の設定と実行
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">最適化設定</h2>
        
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              目標削減率
            </label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={config.targetReduction}
              onChange={(e) => setConfig({...config, targetReduction: parseFloat(e.target.value)})}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">0.6 = 60%削減</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              イプシロン (ε)
            </label>
            <input
              type="number"
              min="0"
              max="0.1"
              step="0.01"
              value={config.epsilon}
              onChange={(e) => setConfig({...config, epsilon: parseFloat(e.target.value)})}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">含意検出の閾値</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              FDR q値
            </label>
            <input
              type="number"
              min="0"
              max="0.1"
              step="0.01"
              value={config.fdrQ}
              onChange={(e) => setConfig({...config, fdrQ: parseFloat(e.target.value)})}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">偽発見率制御</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              イベントファイルパス
            </label>
            <input
              type="text"
              value={config.eventsPath}
              onChange={(e) => setConfig({...config, eventsPath: e.target.value})}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={handleOptimize}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {loading ? (
              <ArrowPathIcon className="animate-spin -ml-1 mr-2 h-5 w-5" />
            ) : (
              <PlayIcon className="-ml-1 mr-2 h-5 w-5" />
            )}
            最適化実行
          </button>
        </div>
      </div>

      {report && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">現在の削減状況</h2>
          
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="bg-gray-50 rounded-lg p-4">
              <dt className="text-sm font-medium text-gray-500">削減率</dt>
              <dd className="mt-1 text-3xl font-semibold text-indigo-600">
                {((report.reduction_by_count || 0) * 100).toFixed(1)}%
              </dd>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <dt className="text-sm font-medium text-gray-500">削減イベント数</dt>
              <dd className="mt-1 text-3xl font-semibold text-gray-900">
                {(report.suppressed_count || 0).toLocaleString()}
              </dd>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <dt className="text-sm font-medium text-gray-500">誤抑制率</dt>
              <dd className="mt-1 text-3xl font-semibold text-green-600">
                {((report.false_suppression_rate || 0) * 100).toFixed(1)}%
              </dd>
            </div>
          </div>

          {report.top_suppressed && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-2">主な削減カテゴリ</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="space-y-2">
                  {report.top_suppressed.slice(0, 10).map((item: any, idx: number) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="text-gray-600">{item.signature}</span>
                      <span className="font-medium text-gray-900">{item.count.toLocaleString()} 件</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
