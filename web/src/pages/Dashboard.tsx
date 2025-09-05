import React, { useEffect, useState } from 'react';
import { useApi } from '../contexts/ApiContext';
import { useTranslation } from 'react-i18next';
import StatsCard from '../components/StatsCard';
import ReductionChart from '../components/ReductionChart';
import AlertsTable from '../components/AlertsTable';
import ActionableAlerts from '../components/ActionableAlerts';
import { ArrowDownIcon, ArrowUpIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export default function Dashboard() {
  const { fetchMetrics, fetchLatestReport } = useApi();
  const { t } = useTranslation();
  const [metrics, setMetrics] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [metricsData, reportData] = await Promise.all([
          fetchMetrics(),
          fetchLatestReport()
        ]);
        setMetrics(metricsData);
        setReport(reportData);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
    // 30秒ごとに更新
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const stats = [
    {
      name: t('dashboard.stats.reductionRate'),
      value: report?.reduction_by_count ? `${(report.reduction_by_count * 100).toFixed(1)}%` : '-',
      change: report?.reduction_by_count > 0.5 ? t('dashboard.stats.targetAchieved') : t('dashboard.stats.improving'),
      changeType: report?.reduction_by_count > 0.5 ? 'positive' : 'neutral',
      icon: ArrowDownIcon,
      color: 'green'
    },
    {
      name: t('dashboard.stats.falseSuppressionRate'),
      value: report?.false_suppression_rate ? `${(report.false_suppression_rate * 100).toFixed(1)}%` : '0.0%',
      change: t('dashboard.stats.safetyEnsured'),
      changeType: 'positive',
      icon: CheckCircleIcon,
      color: 'blue'
    },
    {
      name: t('dashboard.stats.processedEvents'),
      value: report?.total_events?.toLocaleString() || '-',
      change: t('dashboard.stats.last24Hours'),
      changeType: 'neutral',
      icon: ArrowUpIcon,
      color: 'indigo'
    },
    {
      name: t('dashboard.stats.activeRules'),
      value: metrics?.active_rules || '42',
      change: t('dashboard.stats.enabled'),
      changeType: 'neutral',
      icon: ExclamationTriangleIcon,
      color: 'yellow'
    }
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t('dashboard.subtitle')}
        </p>
      </div>

      {/* 統計カード */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatsCard key={stat.name} {...stat} />
        ))}
      </div>

      {/* 重要アラート */}
      <ActionableAlerts />

      {/* グラフとテーブル */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">{t('dashboard.charts.reductionTrend')}</h2>
          <ReductionChart data={report?.history || []} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">{t('dashboard.charts.latestAlerts')}</h2>
          <AlertsTable alerts={report?.recent_alerts || []} />
        </div>
      </div>

      {/* サマリー */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">本日のサマリー</h2>
        <div className="prose prose-sm max-w-none text-gray-600">
          <p>
            過去24時間で <strong>{report?.suppressed_count?.toLocaleString() || 0}</strong> 件のアラートを削減しました。
            削減率は <strong>{((report?.reduction_by_count || 0) * 100).toFixed(1)}%</strong> で、
            {report?.reduction_by_count > 0.5 ? '目標の50%を達成' : '目標の50%に向けて改善中'}しています。
          </p>
          {report?.top_suppressed && report.top_suppressed.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium text-gray-900">主な削減カテゴリ:</h3>
              <ul className="mt-2 space-y-1">
                {report.top_suppressed.slice(0, 5).map((item: any, idx: number) => (
                  <li key={idx}>
                    {item.signature}: <span className="font-medium">{item.count.toLocaleString()}</span> 件
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
