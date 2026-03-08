// API Types

export interface ChatRequest {
  message: string;
  agent_id?: string;
  conversation_id?: string;
}

export interface ChatResponse {
  response: string;
  route?: string;
  conversation_id?: string;
}

export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  role: string | Record<string, unknown>;
  status?: string;
  project_id?: string;
}

export interface AgentConfig {
  metadata?: Record<string, unknown>;
  content: string;
}

export interface Memory {
  id: string;
  content: string;
  timestamp: number;
  type: string;
}

export interface LogEntry {
  message: string;
  datetime?: string;
  source?: string;
  level?: string;
  trace_id?: string;
  run_id?: string;
}

export interface AgentSummary {
  total_runs: number;
  success: number;
  failed: number;
  error: number;
  avg_duration: number;
  route_stats: Record<string, number>;
}

export interface Route {
  name: string;
  description: string;
}

export interface Project {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  agent_count: number;
}

export interface ProjectDetails {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  agents: Agent[];
}

// Token Usage Types
export interface TokenUsageSummary {
  agent_id: string;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  access_count: number;
  last_access_time: string | null;
  updated_at: string | null;
}

export interface ModelTokenStats {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  access_count: number;
}

export interface FunctionTokenStats {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  access_count: number;
}

export interface DateTokenStats {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  access_count: number;
}

export interface ToolCall {
  name: string;
  input: string;
}

export interface LLMCallLog {
  timestamp: string;
  model: string;
  function: string;
  input_tokens: number;
  output_tokens: number;
  input_text?: string;      // 输入文本（完整）
  output_text?: string;     // 输出文本（完整）
  context_sources?: string[];  // 上下文来源地址列表（加载文件列表）
  tool_calls?: ToolCall[];  // 工具调用列表
  // 兼容旧格式
  extra?: {
    input?: string;
    output?: string;
    [key: string]: any;
  };
}

export interface TokenUsageDetails {
  summary: TokenUsageSummary;
  details: {
    by_model: Record<string, ModelTokenStats>;
    by_function: Record<string, FunctionTokenStats>;
    by_date: Record<string, DateTokenStats>;
  };
  llm_logs: LLMCallLog[];  // LLM 调用日志（在根级别）
}

export interface AllAgentsTokenUsage {
  [agent_id: string]: TokenUsageSummary;
}

// Integration Settings Types
export interface Integration {
  id: string;
  name: string;
  url: string;
  provider: string;
  model?: string;
  icon?: string;
  status: 'active' | 'inactive';
  has_key: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface IntegrationFormData {
  name: string;
  url: string;
  provider: string;
  model?: string;
  key?: string;
  icon?: string;
}

// Chat Message Types
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface ApiMessage {
  role: string;
  content: string;
  timestamp?: string;
}
