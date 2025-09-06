import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

interface ReductionChartProps {
  data: Array<{
    date: string;
    reduction: number;
    target: number;
  }>;
}

export default function ReductionChart({ data }: ReductionChartProps) {
  // サンプルデータ（実データがない場合）
  const chartData = data.length > 0 ? data : [
    { date: '2025-09-01', reduction: 45, target: 50 },
    { date: '2025-09-02', reduction: 48, target: 50 },
    { date: '2025-09-03', reduction: 52, target: 50 },
    { date: '2025-09-04', reduction: 55, target: 50 },
    { date: '2025-09-05', reduction: 58.5, target: 50 },
  ].map(d => ({
    ...d,
    reduction: d.reduction,
    target: d.target,
    displayDate: format(new Date(d.date), 'MM/dd'),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis 
          dataKey="displayDate" 
          stroke="#6b7280"
          style={{ fontSize: 12 }}
        />
        <YAxis 
          stroke="#6b7280"
          style={{ fontSize: 12 }}
          domain={[0, 100]}
          tickFormatter={(value) => `${value}%`}
        />
        <Tooltip 
          formatter={(value: number) => `${value.toFixed(1)}%`}
          labelFormatter={(label) => `日付: ${label}`}
        />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="reduction" 
          stroke="#6366f1" 
          strokeWidth={2}
          name="削減率"
          dot={{ fill: '#6366f1', r: 4 }}
          activeDot={{ r: 6 }}
        />
        <Line 
          type="monotone" 
          dataKey="target" 
          stroke="#ef4444" 
          strokeDasharray="5 5"
          strokeWidth={1}
          name="目標"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
