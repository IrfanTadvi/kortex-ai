'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Database, Play, Loader2, Table, Code } from 'lucide-react';
import { api, SQLResult } from '@/lib/api';

export function SQLPanel() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<SQLResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showSQL, setShowSQL] = useState(false);

  const exampleQueries = [
    "Show all employees in Engineering",
    "What is the average salary?",
    "List active projects with their budgets",
    "Who are the department heads?",
    "Show employees hired after 2022",
  ];

  const handleExecute = async (queryText?: string) => {
    const text = queryText || query;
    if (!text.trim()) return;

    setLoading(true);
    setQuery(text);

    try {
      const data = await api.executeSQLQuery(text);
      setResult(data);
    } catch (err: any) {
      setResult({
        status: 'error',
        sql: '',
        results: [],
        explanation: err.message,
        row_count: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-3">
            <Database className="w-7 h-7 text-primary-400" />
            Natural Language SQL
          </h2>
          <p className="text-gray-400">Ask questions in plain English and get SQL results from the company database.</p>
        </div>

        {/* Query Input */}
        <div className="glass-card p-4 mb-6">
          <div className="flex gap-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
              placeholder="Ask a question about the database..."
              className="flex-1 glass-input px-4 py-3 text-white text-sm"
            />
            <button
              onClick={() => handleExecute()}
              disabled={loading || !query.trim()}
              className="glass-button flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Execute
            </button>
          </div>
        </div>

        {/* Example Queries */}
        <div className="flex flex-wrap gap-2 mb-8">
          {exampleQueries.map((eq, i) => (
            <button
              key={i}
              onClick={() => handleExecute(eq)}
              className="glass-button-secondary text-xs text-gray-400 hover:text-white"
            >
              {eq}
            </button>
          ))}
        </div>

        {/* Results */}
        <AnimatePresence mode="wait">
          {result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {/* SQL Query */}
              {result.sql && (
                <div className="glass-card p-4 mb-4">
                  <button
                    onClick={() => setShowSQL(!showSQL)}
                    className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-2"
                  >
                    <Code className="w-4 h-4" />
                    Generated SQL
                  </button>
                  <AnimatePresence>
                    {showSQL && (
                      <motion.pre
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-dark-950 rounded-lg p-4 text-sm text-primary-300 overflow-x-auto border border-white/[0.05]"
                      >
                        {result.sql}
                      </motion.pre>
                    )}
                  </AnimatePresence>
                </div>
              )}

              {/* Explanation */}
              {result.explanation && (
                <div className="glass-card p-4 mb-4">
                  <p className="text-sm text-gray-300">{result.explanation}</p>
                  <p className="text-xs text-gray-500 mt-2">{result.row_count} rows returned</p>
                </div>
              )}

              {/* Results Table */}
              {result.results.length > 0 && (
                <div className="glass-card overflow-hidden">
                  <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06]">
                    <Table className="w-4 h-4 text-primary-400" />
                    <span className="text-sm font-medium text-white">Results</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-white/[0.06]">
                          {Object.keys(result.results[0]).map((key) => (
                            <th key={key} className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.results.map((row, idx) => (
                          <motion.tr
                            key={idx}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: idx * 0.05 }}
                            className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
                          >
                            {Object.values(row).map((value: any, vIdx) => (
                              <td key={vIdx} className="px-4 py-3 text-sm text-gray-300">
                                {typeof value === 'number' ? value.toLocaleString() : String(value)}
                              </td>
                            ))}
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Error State */}
              {result.status === 'error' && (
                <div className="glass-card p-6 text-center">
                  <p className="text-red-400">{result.explanation || 'Query execution failed'}</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Schema Info */}
        {!result && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-card p-6"
          >
            <h3 className="text-lg font-semibold text-white mb-4">Available Tables</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { name: 'employees', desc: 'Employee directory with roles and salaries' },
                { name: 'departments', desc: 'Department info with budgets and locations' },
                { name: 'projects', desc: 'Active and completed project tracking' },
                { name: 'tickets', desc: 'Support ticket management' },
                { name: 'performance_reviews', desc: 'Quarterly performance ratings' },
                { name: 'leave_requests', desc: 'PTO and leave tracking' },
              ].map((table) => (
                <div key={table.name} className="p-4 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                  <div className="flex items-center gap-2 mb-1">
                    <Database className="w-4 h-4 text-primary-400" />
                    <span className="text-sm font-medium text-white">{table.name}</span>
                  </div>
                  <p className="text-xs text-gray-500">{table.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
