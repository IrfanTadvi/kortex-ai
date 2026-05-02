'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3, MessageSquare, FileText, Brain, TrendingUp, Clock
} from 'lucide-react';
import { api, Analytics } from '@/lib/api';

export function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      const data = await api.getAnalytics();
      setAnalytics(data);
    } catch {
      // Use mock data if backend not available
      setAnalytics({
        total_queries: 0,
        total_documents: 0,
        total_sessions: 0,
        avg_confidence: 0,
        queries_today: 0,
        top_sources: [],
        recent_queries: [],
        usage_over_time: [],
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const stats = [
    { label: 'Total Queries', value: analytics?.total_queries || 0, icon: MessageSquare, color: 'from-blue-500 to-cyan-500' },
    { label: 'Documents', value: analytics?.total_documents || 0, icon: FileText, color: 'from-purple-500 to-pink-500' },
    { label: 'Sessions', value: analytics?.total_sessions || 0, icon: Brain, color: 'from-amber-500 to-orange-500' },
    { label: 'Avg Confidence', value: `${((analytics?.avg_confidence || 0) * 100).toFixed(1)}%`, icon: TrendingUp, color: 'from-green-500 to-emerald-500' },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Analytics Dashboard</h2>
          <p className="text-gray-400">Monitor system usage, performance, and query metrics.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {stats.map((stat, idx) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="glass-card p-5"
            >
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-lg`}>
                  <stat.icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-xs text-gray-500">{stat.label}</span>
              </div>
              <p className="text-2xl font-bold text-white">{stat.value}</p>
            </motion.div>
          ))}
        </div>

        {/* Usage Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-6 mb-8"
        >
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary-400" />
            Query Volume (Last 7 Days)
          </h3>
          <div className="flex items-end gap-2 h-40">
            {(analytics?.usage_over_time || []).map((day, idx) => {
              const maxQueries = Math.max(...(analytics?.usage_over_time || []).map(d => d.queries), 1);
              const height = (day.queries / maxQueries) * 100;
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: `${Math.max(height, 4)}%` }}
                    transition={{ delay: 0.5 + idx * 0.05, duration: 0.5 }}
                    className="w-full bg-gradient-to-t from-primary-600 to-primary-400 rounded-t-lg min-h-[4px]"
                  />
                  <span className="text-[10px] text-gray-500">
                    {new Date(day.date).toLocaleDateString('en', { weekday: 'short' })}
                  </span>
                </div>
              );
            })}
            {(!analytics?.usage_over_time || analytics.usage_over_time.length === 0) && (
              <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
                No data yet. Start querying to see usage trends.
              </div>
            )}
          </div>
        </motion.div>

        {/* Recent Queries */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-card p-6"
        >
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary-400" />
            Recent Queries
          </h3>
          <div className="space-y-3">
            {(analytics?.recent_queries || []).map((query, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                <div className="flex-1">
                  <p className="text-sm text-gray-200 truncate">{query.query}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {query.created_at ? new Date(query.created_at).toLocaleString() : ''}
                  </p>
                </div>
                <div className="flex items-center gap-4 ml-4">
                  <div className="text-right">
                    <p className="text-xs text-gray-400">Confidence</p>
                    <p className={`text-sm font-medium ${
                      query.confidence > 0.7 ? 'text-green-400' :
                      query.confidence > 0.4 ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {(query.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-400">Latency</p>
                    <p className="text-sm text-gray-300">{query.latency_ms?.toFixed(0)}ms</p>
                  </div>
                </div>
              </div>
            ))}
            {(!analytics?.recent_queries || analytics.recent_queries.length === 0) && (
              <p className="text-gray-500 text-sm text-center py-6">No queries logged yet.</p>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
