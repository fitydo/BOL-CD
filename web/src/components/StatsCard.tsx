import React from 'react';
import clsx from 'clsx';

interface StatsCardProps {
  name: string;
  value: string;
  change: string;
  changeType: 'positive' | 'negative' | 'neutral';
  icon: React.ComponentType<{ className?: string }>;
  color: 'green' | 'red' | 'blue' | 'yellow' | 'indigo';
}

export default function StatsCard({ name, value, change, changeType, icon: Icon, color }: StatsCardProps) {
  const colorClasses = {
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    blue: 'bg-blue-50 text-blue-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    indigo: 'bg-indigo-50 text-indigo-600',
  };

  const changeColors = {
    positive: 'text-green-600',
    negative: 'text-red-600',
    neutral: 'text-gray-500',
  };

  return (
    <div className="bg-white rounded-lg shadow px-5 py-6">
      <div className="flex items-center">
        <div className={clsx('flex-shrink-0 rounded-md p-3', colorClasses[color])}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">{name}</dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900">{value}</div>
              <div className={clsx('ml-2 text-sm', changeColors[changeType])}>
                {change}
              </div>
            </dd>
          </dl>
        </div>
      </div>
    </div>
  );
}
