import React, { useState, useEffect } from 'react';
import { tokenUsageApi } from '../services/api';
import type { TokenUsageDetails, AllAgentsTokenUsage } from '../types';

interface TokenUsagePanelProps {
  agentId?: string;
}

interface AgentCardProps {
  agentId: string;
  summary: {
    agent_id: string;
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    access_count: number;
    last_access_time: string | null;
    updated_at: string | null;
  };
  onClick: (agentId: string) => void;
}

const AgentCard: React.FC<AgentCardProps> = ({ agentId, summary, onClick }) => {
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(2) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(2) + 'K';
    }
    return num.toString();
  };

  const formatTime = (timeStr: string | null): string => {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN');
  };

  return (
    <div
      onClick={() => onClick(agentId)}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 cursor-pointer hover:shadow-lg transition-shadow"
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        {agentId}
      </h3>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-gray-500 dark:text-gray-400">总 Token:</span>
          <span className="ml-2 text-blue-600 dark:text-blue-400 font-medium">
            {formatNumber(summary.total_tokens)}
          </span>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">访问次数:</span>
          <span className="ml-2 text-green-600 dark:text-green-400 font-medium">
            {summary.access_count}
          </span>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">输入:</span>
          <span className="ml-2 text-purple-600 dark:text-purple-400">
            {formatNumber(summary.input_tokens)}
          </span>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">输出:</span>
          <span className="ml-2 text-orange-600 dark:text-orange-400">
            {formatNumber(summary.output_tokens)}
          </span>
        </div>
      </div>
      <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
        最后访问：{formatTime(summary.last_access_time)}
      </div>
    </div>
  );
};

const TokenUsagePanel: React.FC<TokenUsagePanelProps> = ({ agentId }) => {
  const [allUsage, setAllUsage] = useState<AllAgentsTokenUsage | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(agentId || null);
  const [details, setDetails] = useState<TokenUsageDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAllUsage = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await tokenUsageApi.getAll();
      setAllUsage(response.data.all_usage);
    } catch (err) {
      setError('加载 Token 使用数据失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadAgentDetails = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await tokenUsageApi.get(id);
      setDetails(response.data);
      setSelectedAgent(id);
    } catch (err) {
      setError(`加载 ${id} 的详细信息失败`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!selectedAgent) return;
    if (!confirm(`确定要重置 ${selectedAgent} 的 Token 使用统计吗？`)) return;

    try {
      await tokenUsageApi.reset(selectedAgent);
      await loadAllUsage();
      setDetails(null);
      setSelectedAgent(null);
    } catch (err) {
      setError('重置失败');
    }
  };

  useEffect(() => {
    loadAllUsage();
  }, []);

  const formatNumber = (num: number): string => {
    return num.toLocaleString('zh-CN');
  };

  const formatTime = (timeStr: string | null): string => {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN');
  };

  if (loading && !allUsage) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500 dark:text-gray-400">加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Token 使用统计
        </h2>
        {selectedAgent && (
          <button
            onClick={() => {
              setSelectedAgent(null);
              setDetails(null);
            }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            返回列表
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg">
          {error}
        </div>
      )}

      {selectedAgent && details ? (
        /* 详细信息视图 */
        <div className="space-y-6">
          {/* 摘要卡片 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {selectedAgent} - 使用摘要
              </h3>
              <button
                onClick={handleReset}
                className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
              >
                重置统计
              </button>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {formatNumber(details.summary.total_tokens)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">总 Token</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {formatNumber(details.summary.input_tokens)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">输入 Token</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {formatNumber(details.summary.output_tokens)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">输出 Token</div>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">访问次数:</span>
                <span className="ml-2 font-medium">{details.summary.access_count}</span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">最后访问:</span>
                <span className="ml-2 font-medium">{formatTime(details.summary.last_access_time)}</span>
              </div>
            </div>
          </div>

          {/* 按模型统计 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              按模型统计
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b dark:border-gray-700">
                    <th className="text-left py-2 text-gray-500 dark:text-gray-400">模型</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">输入</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">输出</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">总计</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">次数</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(details.details.by_model).map(([model, stats]) => (
                    <tr key={model} className="border-b dark:border-gray-700">
                      <td className="py-2 font-medium">{model}</td>
                      <td className="text-right text-purple-600 dark:text-purple-400">
                        {formatNumber(stats.input_tokens)}
                      </td>
                      <td className="text-right text-orange-600 dark:text-orange-400">
                        {formatNumber(stats.output_tokens)}
                      </td>
                      <td className="text-right font-medium">{formatNumber(stats.total_tokens)}</td>
                      <td className="text-right text-green-600 dark:text-green-400">
                        {stats.access_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 按功能统计 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              按功能统计
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b dark:border-gray-700">
                    <th className="text-left py-2 text-gray-500 dark:text-gray-400">功能</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">输入</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">输出</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">总计</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">次数</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(details.details.by_function).map(([func, stats]) => {
                    const funcNames: Record<string, string> = {
                      think: '决策',
                      chat: '对话',
                      evolution: '进化',
                      analysis: '分析',
                      other: '其他',
                    };
                    return (
                      <tr key={func} className="border-b dark:border-gray-700">
                        <td className="py-2 font-medium">{funcNames[func] || func} ({func})</td>
                        <td className="text-right text-purple-600 dark:text-purple-400">
                          {formatNumber(stats.input_tokens)}
                        </td>
                        <td className="text-right text-orange-600 dark:text-orange-400">
                          {formatNumber(stats.output_tokens)}
                        </td>
                        <td className="text-right font-medium">{formatNumber(stats.total_tokens)}</td>
                        <td className="text-right text-green-600 dark:text-green-400">
                          {stats.access_count}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 每日统计 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              每日统计
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b dark:border-gray-700">
                    <th className="text-left py-2 text-gray-500 dark:text-gray-400">日期</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">输入</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">输出</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">总计</th>
                    <th className="text-right text-gray-500 dark:text-gray-400">次数</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(details.details.by_date)
                    .sort(([a], [b]) => b.localeCompare(a))
                    .map(([date, stats]) => (
                      <tr key={date} className="border-b dark:border-gray-700">
                        <td className="py-2 font-medium">{date}</td>
                        <td className="text-right text-purple-600 dark:text-purple-400">
                          {formatNumber(stats.input_tokens)}
                        </td>
                        <td className="text-right text-orange-600 dark:text-orange-400">
                          {formatNumber(stats.output_tokens)}
                        </td>
                        <td className="text-right font-medium">{formatNumber(stats.total_tokens)}</td>
                        <td className="text-right text-green-600 dark:text-green-400">
                          {stats.access_count}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* 列表视图 */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {allUsage &&
            Object.entries(allUsage).map(([agentId, summary]) => (
              <AgentCard
                key={agentId}
                agentId={agentId}
                summary={summary}
                onClick={loadAgentDetails}
              />
            ))}
          {(!allUsage || Object.keys(allUsage).length === 0) && (
            <div className="col-span-full text-center text-gray-500 dark:text-gray-400 py-8">
              暂无 Token 使用数据
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TokenUsagePanel;
