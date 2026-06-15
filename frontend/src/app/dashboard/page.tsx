'use client';

/**
 * Monitoring Dashboard — LLM cost, latency, and quality metrics.
 *
 * Displays:
 * - Token usage and cost over time
 * - Latency percentiles (p50, p95, p99)
 * - Quality metrics (faithfulness, relevance trends)
 * - Per-model breakdown
 */

import { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

// Mock data for dashboard — in production, fetched from /api/v1/metrics
const MOCK_COST_DATA = [
  { date: 'Mon', openai: 2.4, anthropic: 1.8, total: 4.2 },
  { date: 'Tue', openai: 3.1, anthropic: 2.2, total: 5.3 },
  { date: 'Wed', openai: 2.8, anthropic: 1.9, total: 4.7 },
  { date: 'Thu', openai: 3.5, anthropic: 2.5, total: 6.0 },
  { date: 'Fri', openai: 4.2, anthropic: 3.1, total: 7.3 },
  { date: 'Sat', openai: 1.8, anthropic: 1.2, total: 3.0 },
  { date: 'Sun', openai: 1.5, anthropic: 0.9, total: 2.4 },
];

const MOCK_LATENCY_DATA = [
  { hour: '00:00', p50: 450, p95: 1200, p99: 2800 },
  { hour: '04:00', p50: 380, p95: 980, p99: 2200 },
  { hour: '08:00', p50: 520, p95: 1500, p99: 3200 },
  { hour: '12:00', p50: 680, p95: 1800, p99: 4100 },
  { hour: '16:00', p50: 590, p95: 1600, p99: 3600 },
  { hour: '20:00', p50: 420, p95: 1100, p99: 2500 },
];

const MOCK_QUALITY_DATA = [
  { date: 'Mon', faithfulness: 0.88, relevance: 0.82, correctness: 0.79 },
  { date: 'Tue', faithfulness: 0.91, relevance: 0.85, correctness: 0.83 },
  { date: 'Wed', faithfulness: 0.87, relevance: 0.80, correctness: 0.78 },
  { date: 'Thu', faithfulness: 0.93, relevance: 0.88, correctness: 0.85 },
  { date: 'Fri', faithfulness: 0.89, relevance: 0.84, correctness: 0.81 },
  { date: 'Sat', faithfulness: 0.92, relevance: 0.87, correctness: 0.84 },
  { date: 'Sun', faithfulness: 0.90, relevance: 0.86, correctness: 0.82 },
];

interface MetricCard {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
}

export default function DashboardPage() {
  const [metrics] = useState<MetricCard[]>([
    { label: 'Total Queries Today', value: '1,284', change: '+12%', trend: 'up' },
    { label: 'Avg Latency (p50)', value: '520ms', change: '-8%', trend: 'down' },
    { label: 'Cost Today', value: '$7.32', change: '+15%', trend: 'up' },
    { label: 'Quality Score', value: '0.87', change: '+2%', trend: 'up' },
  ]);

  return (
    <div className="p-6 overflow-y-auto h-full">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">System Dashboard</h1>

        {/* Metric cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-xl border bg-white p-4 shadow-sm"
            >
              <p className="text-xs text-gray-500">{metric.label}</p>
              <p className="text-2xl font-bold text-gray-800 mt-1">{metric.value}</p>
              <p
                className={`text-xs mt-1 ${
                  metric.trend === 'up' && metric.label.includes('Cost')
                    ? 'text-red-500'
                    : metric.trend === 'up'
                    ? 'text-green-500'
                    : metric.trend === 'down' && metric.label.includes('Latency')
                    ? 'text-green-500'
                    : 'text-gray-500'
                }`}
              >
                {metric.change} vs yesterday
              </p>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-2 gap-6">
          {/* Cost over time */}
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">
              LLM Cost by Provider ($)
            </h2>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={MOCK_COST_DATA}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="openai"
                  stackId="1"
                  stroke="#10b981"
                  fill="#10b98133"
                  name="OpenAI"
                />
                <Area
                  type="monotone"
                  dataKey="anthropic"
                  stackId="1"
                  stroke="#8b5cf6"
                  fill="#8b5cf633"
                  name="Anthropic"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Latency percentiles */}
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">
              Response Latency (ms)
            </h2>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={MOCK_LATENCY_DATA}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="p50" fill="#3b82f6" name="p50" />
                <Bar dataKey="p95" fill="#f59e0b" name="p95" />
                <Bar dataKey="p99" fill="#ef4444" name="p99" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Quality metrics */}
          <div className="rounded-xl border bg-white p-4 shadow-sm col-span-2">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">
              RAG Quality Metrics (7-day trend)
            </h2>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={MOCK_QUALITY_DATA}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis domain={[0.5, 1.0]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="faithfulness"
                  stroke="#10b981"
                  fill="#10b98122"
                  name="Faithfulness"
                />
                <Area
                  type="monotone"
                  dataKey="relevance"
                  stroke="#3b82f6"
                  fill="#3b82f622"
                  name="Relevance"
                />
                <Area
                  type="monotone"
                  dataKey="correctness"
                  stroke="#8b5cf6"
                  fill="#8b5cf622"
                  name="Correctness"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
