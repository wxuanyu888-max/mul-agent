import { useEffect, useState } from 'react';
import { Search, RefreshCw, FileText } from 'lucide-react';
import { logsApi } from '../../services/api';
import type { LogEntry } from '../../types';

export function LogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ level: '', keyword: '', source: '' });

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await logsApi.getLogs(
        100,
        filter.level || undefined,
        filter.keyword || undefined,
        filter.source || undefined
      );
      setLogs(response.data.logs);
      console.log('[LogViewer] Fetched logs:', response.data.logs.length);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter.level, filter.source, filter.keyword]);

  const getLevelColor = (level?: string) => {
    switch (level?.toLowerCase()) {
      case 'error':
      case 'critical':
        return 'text-red-600 bg-red-50';
      case 'warning':
        return 'text-amber-600 bg-amber-50';
      case 'info':
        return 'text-blue-600 bg-blue-50';
      case 'debug':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-700 bg-gray-50';
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-gray-400" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Logs</h2>
              <p className="text-sm text-gray-500">View system logs</p>
            </div>
          </div>
          <button
            onClick={fetchLogs}
            className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700 font-medium text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <select
            value={filter.level}
            onChange={(e) => setFilter({ ...filter, level: e.target.value })}
            className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Levels</option>
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>

          <select
            value={filter.source}
            onChange={(e) => setFilter({ ...filter, source: e.target.value })}
            className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Sources</option>
            <option value="brain">Brain</option>
            <option value="router">Router</option>
            <option value="agent">Agent</option>
          </select>

          <div className="flex-1 relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search logs..."
              value={filter.keyword}
              onChange={(e) => setFilter({ ...filter, keyword: e.target.value })}
              className="w-full bg-gray-50 border border-gray-200 rounded-lg pl-9 pr-4 py-2 text-gray-700 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Log List */}
      <div className="flex-1 overflow-y-auto px-6 py-4 font-mono text-sm bg-gray-50">
        {loading && logs.length === 0 ? (
          <div className="text-center py-8">
            <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No logs found
          </div>
        ) : (
          <div className="space-y-1.5">
            {logs.map((log, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border ${getLevelColor(log.level)} border-transparent hover:border-gray-200 transition-colors`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-gray-400 text-xs whitespace-nowrap">
                    {log.datetime ? new Date(log.datetime).toLocaleString() : ''}
                  </span>
                  <span className="uppercase text-xs font-semibold px-2 py-0.5 rounded-full bg-white/50">
                    {log.level || 'INFO'}
                  </span>
                  {log.source && (
                    <span className="text-blue-600 text-xs font-medium">{log.source}</span>
                  )}
                  <span className="flex-1">{log.message}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
