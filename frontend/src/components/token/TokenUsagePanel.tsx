import React, { useState, useEffect } from 'react';
import { tokenUsageApi, infoApi } from '../../services/api';
import type { TokenUsageDetails, AllAgentsTokenUsage, LLMCallLog, TokenUsageSummary, ToolCall } from '../../types';

interface TokenUsagePanelProps {
  agentId?: string;
}

// 合并后的调用日志记录（包含 agent_id）
interface MergedLLMLog {
  agent_id: string;
  timestamp: string;
  model: string;
  function: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  input_text?: string;
  output_text?: string;
  context_sources?: string[];
  tool_calls?: ToolCall[];
  extra?: {
    input?: string;
    output?: string;
  };
}

const TokenUsagePanel: React.FC<TokenUsagePanelProps> = ({ agentId }) => {
  const [allUsage, setAllUsage] = useState<AllAgentsTokenUsage | null>(null);
  const [allLogs, setAllLogs] = useState<MergedLLMLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedLogIds, setExpandedLogIds] = useState<Set<string>>(new Set());
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  // 存储已加载的文件内容
  const [loadedFilesContent, setLoadedFilesContent] = useState<Record<string, { content: string; size?: number; error?: string }>>({});
  const [loadingFiles, setLoadingFiles] = useState(false);

  // 分页状态 - 表 1（Agent 统计）
  const [table1Page, setTable1Page] = useState(1);
  const TABLE1_PAGE_SIZE = 10;

  // 分页状态 - 表 2（LLM 调用明细）- 每页显示 10 条
  const [table2Page, setTable2Page] = useState(1);
  const TABLE2_PAGE_SIZE = 10;
  // 不判断是否超过页数，始终显示分页控件

  // 加载所有 Agent 的 Token 使用数据和日志
  const loadAllUsage = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await tokenUsageApi.getAll();
      setAllUsage(response.data.all_usage);
      // 自动加载日志（在 loadAllLogs 中重置分页状态）
      await loadAllLogs(response.data.all_usage);
      setLastUpdated(new Date());
    } catch (err) {
      setError('加载 Token 使用数据失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 单独加载日志的方法
  const loadAllLogs = async (allUsage: AllAgentsTokenUsage) => {
    setLoadingLogs(true);
    try {
      const allLogsData: MergedLLMLog[] = [];
      const agents = Object.keys(allUsage);

      await Promise.all(
        agents.map(async (agentId) => {
          try {
            const agentResponse = await tokenUsageApi.get(agentId);
            const logs = agentResponse?.data?.llm_logs || [];
            logs.forEach((log: LLMCallLog) => {
              allLogsData.push({
                agent_id: agentId,
                ...log,
                total_tokens: log.input_tokens + log.output_tokens,
              });
            });
          } catch (err) {
            console.error(`Failed to load logs for ${agentId}:`, err);
            // Continue loading other agents' logs even if one fails
          }
        })
      );

      // 按时间戳倒序排列
      allLogsData.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      // 设置日志数据
      setAllLogs(allLogsData);
    } catch (err) {
      console.error('Failed to load logs:', err);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    loadAllUsage();

    // 定时刷新，实现实时同步（每 30 秒刷新一次）
    const interval = setInterval(() => {
      loadAllUsage();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // 表 1 分页计算
  const table1Data = allUsage ? Object.entries(allUsage).sort(
    ([, a], [, b]) => (b as TokenUsageSummary).total_tokens - (a as TokenUsageSummary).total_tokens
  ) : [];
  const table1TotalPages = Math.ceil(table1Data.length / TABLE1_PAGE_SIZE);
  const table1PageData = table1Data.slice(
    (table1Page - 1) * TABLE1_PAGE_SIZE,
    table1Page * TABLE1_PAGE_SIZE
  );

  // 表 2 分页计算 - 简化，不计算总页数
  const table2PageData = allLogs.slice(
    (table2Page - 1) * TABLE2_PAGE_SIZE,
    table2Page * TABLE2_PAGE_SIZE
  );

  // 页码改变时的处理 - 滚回表格顶部
  const handleTable1PageChange = (newPage: number) => {
    setTable1Page(newPage);
  };

  const handleTable2PageChange = (newPage: number) => {
    setTable2Page(newPage);
    setExpandedLogIds(new Set()); // 展开的行重置
  };

  // 使用 row key 来管理展开状态，而不是索引
  const toggleExpand = (rowKey: string) => {
    const newExpanded = new Set(expandedLogIds);
    if (newExpanded.has(rowKey)) {
      newExpanded.delete(rowKey);
    } else {
      newExpanded.add(rowKey);
      // 展开时加载文件内容
      const log = allLogs.find((log, idx) => `${log.agent_id}-${log.timestamp}-${idx}` === rowKey);
      if (log && log.context_sources && log.context_sources.length > 0) {
        loadFilesContent(log.context_sources);
      }
    }
    setExpandedLogIds(newExpanded);
  };

  // 加载文件内容
  const loadFilesContent = async (filePaths: string[]) => {
    setLoadingFiles(true);
    try {
      // 过滤出未加载的文件
      const unloadedFiles = filePaths.filter(path => !loadedFilesContent[path]);
      if (unloadedFiles.length === 0) {
        setLoadingFiles(false);
        return;
      }

      const response = await infoApi.getFilesBatch(unloadedFiles);
      setLoadedFilesContent(prev => ({
        ...prev,
        ...response.data.files
      }));
    } catch (err) {
      console.error('Failed to load files content:', err);
    } finally {
      setLoadingFiles(false);
    }
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString('zh-CN');
  };

  const formatTime = (timeStr: string | null): string => {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 兼容旧格式和新格式
  const getInputText = (log: MergedLLMLog) => log.input_text || log.extra?.input || '-';
  const getOutputText = (log: MergedLLMLog) => log.output_text || log.extra?.output || '-';
  const getContextSources = (log: MergedLLMLog) => log.context_sources || [];
  const getToolCalls = (log: MergedLLMLog) => log.tool_calls || [];

  const funcNames: Record<string, string> = {
    think: '决策',
    chat: '对话',
    evolution: '进化',
    analysis: '分析',
    other: '其他',
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
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Token 使用统计
        </h2>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg">
          {error}
        </div>
      )}

      {/* 表 1：按 Agent 统计 */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          表 1：按 Agent 统计汇总
          {table1Data.length > 0 && (
            <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
              （第 {table1Page}/{table1TotalPages} 页，共 {table1Data.length} 条记录）
            </span>
          )}
        </h3>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="text-left py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">Agent ID</th>
                <th className="text-right py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">输入 Token</th>
                <th className="text-right py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">输出 Token</th>
                <th className="text-right py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">总 Token</th>
                <th className="text-right py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">调用次数</th>
                <th className="text-left py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">最后访问时间</th>
              </tr>
            </thead>
            <tbody>
              {table1PageData.length > 0 && table1PageData.map(([agentId, summary]) => (
                <tr key={agentId} className="border-t dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{agentId}</td>
                  <td className="text-right py-3 px-4 text-purple-600 dark:text-purple-400">
                    {formatNumber((summary as TokenUsageSummary).input_tokens)}
                  </td>
                  <td className="text-right py-3 px-4 text-orange-600 dark:text-orange-400">
                    {formatNumber((summary as TokenUsageSummary).output_tokens)}
                  </td>
                  <td className="text-right py-3 px-4 font-semibold text-blue-600 dark:text-blue-400">
                    {formatNumber((summary as TokenUsageSummary).total_tokens)}
                  </td>
                  <td className="text-right py-3 px-4 text-green-600 dark:text-green-400">
                    {formatNumber((summary as TokenUsageSummary).access_count)}
                  </td>
                  <td className="text-left py-3 px-4 text-gray-500 dark:text-gray-400">
                    {formatTime((summary as TokenUsageSummary).last_access_time)}
                  </td>
                </tr>
              ))}
              {table1Data.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-500 dark:text-gray-400">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot className="bg-gray-100 dark:bg-gray-900/50">
              <tr className="font-semibold">
                <td className="py-3 px-4 text-gray-900 dark:text-white">合计</td>
                <td className="text-right py-3 px-4 text-purple-600 dark:text-purple-400">
                  {formatNumber(Object.values(allUsage || {}).reduce((sum, s) => sum + (s as TokenUsageSummary).input_tokens, 0))}
                </td>
                <td className="text-right py-3 px-4 text-orange-600 dark:text-orange-400">
                  {formatNumber(Object.values(allUsage || {}).reduce((sum, s) => sum + (s as TokenUsageSummary).output_tokens, 0))}
                </td>
                <td className="text-right py-3 px-4 text-blue-600 dark:text-blue-400">
                  {formatNumber(Object.values(allUsage || {}).reduce((sum, s) => sum + (s as TokenUsageSummary).total_tokens, 0))}
                </td>
                <td className="text-right py-3 px-4 text-green-600 dark:text-green-400">
                  {formatNumber(Object.values(allUsage || {}).reduce((sum, s) => sum + (s as TokenUsageSummary).access_count, 0))}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
        {/* 分页控件 - 表 1 */}
        {table1TotalPages > 1 && (
          <div className="flex items-center justify-between mt-3">
            <button
              onClick={() => handleTable1PageChange(table1Page - 1)}
              disabled={table1Page === 1}
              className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              上一页
            </button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, table1TotalPages) }, (_, i) => {
                let pageNum;
                if (table1TotalPages <= 5) {
                  pageNum = i + 1;
                } else if (table1Page <= 3) {
                  pageNum = i + 1;
                } else if (table1Page >= table1TotalPages - 2) {
                  pageNum = table1TotalPages - 4 + i;
                } else {
                  pageNum = table1Page - 2 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => handleTable1PageChange(pageNum)}
                    className={`w-8 h-8 text-sm rounded ${
                      table1Page === pageNum
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            <button
              onClick={() => handleTable1PageChange(table1Page + 1)}
              disabled={table1Page === table1TotalPages}
              className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              下一页
            </button>
          </div>
        )}
      </div>

      {/* 表 2：LLM 调用明细表 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              表 2：LLM 调用明细
            </h3>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {loadingLogs ? '加载中...' : `(共 ${allLogs.length} 条记录)`}
              </span>
              {lastUpdated && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  • 最后更新：{lastUpdated.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}
              <span className="text-xs text-green-600 dark:text-green-500 flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                自动同步中
              </span>
            </div>
          </div>
        </div>
        {/* 表格容器 - 固定高度，内部可滚动 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-auto max-h-[calc(100vh-280px)]">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-900 sticky top-0 z-10">
              <tr>
                <th className="text-left py-3 px-4 text-gray-500 dark:text-gray-400 font-medium w-12"></th>
                <th className="text-left py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">时间戳</th>
                <th className="text-left py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">Agent</th>
                <th className="text-left py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">模型</th>
                <th className="text-left py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">功能</th>
                <th className="text-right py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">输入</th>
                <th className="text-right py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">输出</th>
                <th className="text-right py-3 px-4 text-gray-500 dark:text-gray-400 font-medium">总计</th>
              </tr>
            </thead>
            <tbody>
              {/* 加载中状态 */}
              {loadingLogs && (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <div className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      正在加载 LLM 调用记录...
                    </div>
                  </td>
                </tr>
              )}
              {/* 有数据 - 渲染数据行（使用分页数据） */}
              {!loadingLogs && table2PageData.map((log, pageIndex) => {
                const rowKey = `${log.agent_id}-${log.timestamp}-${pageIndex}`;
                const isExpanded = expandedLogIds.has(rowKey as any);
                return (
                  <React.Fragment key={rowKey}>
                    <tr
                      className={`border-t dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 ${
                        isExpanded ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                      }`}
                      onClick={() => toggleExpand(rowKey)}
                    >
                      <td className="py-3 px-4 text-center">
                        <svg
                          className={`w-4 h-4 inline transition-transform ${
                            isExpanded ? 'rotate-180' : ''
                          }`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </td>
                      <td className="py-3 px-4 text-gray-500 dark:text-gray-400">
                        {formatTime(log.timestamp)}
                      </td>
                      <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">
                        {log.agent_id}
                      </td>
                      <td className="py-3 px-4 text-gray-500 dark:text-gray-400">
                        {log.model}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                          {funcNames[log.function] || log.function}
                        </span>
                      </td>
                      <td className="text-right py-3 px-4 text-purple-600 dark:text-purple-400">
                        {formatNumber(log.input_tokens)}
                      </td>
                      <td className="text-right py-3 px-4 text-orange-600 dark:text-orange-400">
                        {formatNumber(log.output_tokens)}
                      </td>
                      <td className="text-right py-3 px-4 font-semibold text-blue-600 dark:text-blue-400">
                        {formatNumber(log.total_tokens)}
                      </td>
                    </tr>

                    {/* 展开的详细信息 - 放在可滚动容器中 */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={8} className="border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                          {/* 固定高度的可滚动容器 */}
                          <div className="max-h-[70vh] overflow-y-auto p-4 space-y-4">
                            {/* 输入文本 */}
                            <div>
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase">
                                  📥 输入文本
                                </span>
                              </div>
                              <pre className="bg-white dark:bg-gray-800 rounded p-3 text-xs text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap break-words border border-gray-200 dark:border-gray-700">
                                {getInputText(log)}
                              </pre>
                            </div>

                            {/* 输出文本 */}
                            <div>
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-semibold text-orange-600 dark:text-orange-400 uppercase">
                                  📤 输出文本（LLM 响应）
                                </span>
                              </div>
                              <pre className="bg-white dark:bg-gray-800 rounded p-3 text-xs text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap break-words border border-gray-200 dark:border-gray-700">
                                {getOutputText(log)}
                              </pre>
                            </div>

                            {/* 加载文件内容（完整显示） */}
                            {getContextSources(log).length > 0 && (
                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase">
                                    📁 加载的文件内容（上下文来源）
                                  </span>
                                  <span className="text-xs text-gray-500">
                                    （共 {getContextSources(log).length} 个文件）
                                  </span>
                                </div>
                                <div className="space-y-3">
                                  {getContextSources(log).map((filePath, idx) => {
                                    const fileData = loadedFilesContent[filePath];
                                    return (
                                      <div key={idx} className="bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 overflow-hidden">
                                        {/* 文件头：显示路径和大小 */}
                                        <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                                          <span className="text-xs font-mono text-gray-600 dark:text-gray-400 truncate max-w-md">
                                            {filePath}
                                          </span>
                                          <div className="flex items-center gap-2">
                                            {fileData?.error && (
                                              <span className="text-xs text-red-500">{fileData.error}</span>
                                            )}
                                            {fileData?.size && (
                                              <span className="text-xs text-gray-400">
                                                {(fileData.size / 1024).toFixed(1)} KB
                                              </span>
                                            )}
                                            {!fileData && loadingFiles && (
                                              <span className="text-xs text-gray-400 animate-pulse">加载中...</span>
                                            )}
                                          </div>
                                        </div>
                                        {/* 文件内容 */}
                                        <div className="max-h-64 overflow-y-auto">
                                          {fileData?.content ? (
                                            <pre className="w-full p-3 text-xs text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap break-words font-mono">
                                              {fileData.content.length > 5000
                                                ? fileData.content.slice(0, 5000) + '\n\n... (文件内容过长，仅显示前 5000 字符)'
                                                : fileData.content}
                                            </pre>
                                          ) : fileData?.error ? (
                                            <div className="p-4 text-sm text-red-500">
                                              无法加载文件：{fileData.error}
                                            </div>
                                          ) : (
                                            <div className="p-4 text-sm text-gray-400 animate-pulse">
                                              正在加载文件内容...
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* 工具调用 */}
                            {getToolCalls(log).length > 0 && (
                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase">
                                    🛠️ 工具调用
                                  </span>
                                </div>
                                <div className="space-y-2">
                                  {getToolCalls(log).map((tool, idx) => (
                                    <div key={idx} className="bg-white dark:bg-gray-800 rounded p-2 text-xs border border-gray-200 dark:border-gray-700">
                                      <span className="font-medium text-gray-900 dark:text-white">{tool.name}</span>
                                      <span className="text-gray-500 dark:text-gray-400 ml-2">:</span>
                                      <span className="text-gray-700 dark:text-gray-300 ml-1">{tool.input}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              {/* 无数据 */}
              {!loadingLogs && table2PageData.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-gray-500 dark:text-gray-400">
                    暂无 LLM 调用记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* 分页控件 - 表 2 - 始终显示分页控件 */}
        {allLogs.length > 0 && (
          <div className="flex items-center justify-between mt-3">
            <span className="text-xs text-gray-500">
              记录数：{allLogs.length} (当前第 {table2Page} 页)
            </span>
            <button
              onClick={() => handleTable2PageChange(table2Page - 1)}
              disabled={table2Page === 1}
              className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              上一页
            </button>
            <div className="flex items-center gap-1">
              {Array.from({ length: 5 }, (_, i) => table2Page - 2 + i).filter(p => p >= 1).map((pageNum) => (
                <button
                  key={pageNum}
                  onClick={() => handleTable2PageChange(pageNum)}
                  className={`w-8 h-8 text-sm rounded ${
                    table2Page === pageNum
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {pageNum}
                </button>
              ))}
            </div>
            <button
              onClick={() => {
                const nextPage = table2Page + 1
                if (nextPage * TABLE2_PAGE_SIZE > allLogs.length) {
                  setTable2Page(1) // 循环到第一页
                } else {
                  setTable2Page(nextPage)
                }
              }}
              disabled={table2Page * TABLE2_PAGE_SIZE >= allLogs.length}
              className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TokenUsagePanel;
