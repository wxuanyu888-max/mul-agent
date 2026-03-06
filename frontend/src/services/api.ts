import axios from 'axios';
import type {
  ChatRequest,
  ChatResponse,
  Agent,
  AgentConfig,
  Memory,
  LogEntry,
  AgentSummary,
  Route,
  Project,
  ProjectDetails,
  TokenUsageSummary,
  TokenUsageDetails,
  AllAgentsTokenUsage,
} from '../types';

// Use relative path to work with Vite proxy in development
const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Chat API
export const chatApi = {
  sendMessage: (request: ChatRequest) =>
    api.post<ChatResponse>('/chat', request),

  getHistory: (limit: number = 20) =>
    api.get<{ history: Array<{ role: string; content: string }>; total: number }>('/chat/history', { params: { limit } }),

  getSessions: () =>
    api.get<{ sessions: Array<{ session_id: string; path: string }> }>('/chat/sessions'),
};

// Agents API
export const agentsApi = {
  list: () =>
    api.get<{ agents: Agent[] }>('/agents'),

  get: (agentId: string) =>
    api.get<{ agent_id: string; soul: AgentConfig; user: AgentConfig; skill: AgentConfig; memory: AgentConfig }>(`/agents/${agentId}`),

  getConfig: (agentId: string, configType: string = 'all') =>
    api.get<Record<string, AgentConfig>>(`/agents/${agentId}/config`, { params: { config_type: configType } }),

  updateConfig: (agentId: string, configType: string, content: string, metadata?: Record<string, unknown>) =>
    api.put(`/agents/${agentId}/config`, { config_type: configType, content, metadata }),

  getStatus: (agentId: string) =>
    api.get<{ agent_id: string; status: string; session_id: string | null }>(`/agents/${agentId}/status`),
};

// Memory API
export const memoryApi = {
  getShortTerm: (agentId: string = 'core_brain', limit: number = 20) =>
    api.get<{ memories: Memory[]; total: number }>('/memory/short-term', { params: { agentId, limit } }),

  getLongTerm: (agentId: string = 'core_brain', limit: number = 20) =>
    api.get<{ memories: Memory[]; total: number }>('/memory/long-term', { params: { agentId, limit } }),

  getHandover: (agentId: string = 'core_brain') =>
    api.get<{ memories: Memory[] }>('/memory/handover', { params: { agentId } }),

  write: (content: string, agentId: string = 'core_brain', memoryType: string = 'short_term', metadata?: Record<string, unknown>) =>
    api.post<{ status: string; memory_id: string; path: string }>('/memory/write', {
      content,
      agentId,
      memoryType,
      metadata,
    }),

  delete: (memoryId: string, agentId: string = 'core_brain', memoryType: string = 'short_term') =>
    api.delete(`/memory/${memoryId}`, { params: { agentId, memoryType } }),
};

// Logs API
export const logsApi = {
  getLogs: (limit: number = 100, level?: string, keyword?: string, source?: string) =>
    api.get<{ logs: LogEntry[]; total: number }>('/logs', { params: { limit, level, keyword, source } }),

  getStats: () =>
    api.get<Record<string, unknown>>('/logs/stats'),

  getFiles: () =>
    api.get<{ files: Array<{ filename: string; path: string; size: number; modified: string }> }>('/logs/files'),
};

// Info API
export const infoApi = {
  getSummary: () =>
    api.get<AgentSummary>('/info/summary'),

  getRoutes: () =>
    api.get<{ routes: Route[] }>('/info/routes'),

  getRuns: (limit: number = 10) =>
    api.get<{ runs: Array<Record<string, unknown>> }>('/info/runs', { params: { limit } }),

  getCurrentWorkflow: () =>
    api.get<{ active: boolean; run_id?: string; input?: string; status?: string; phase?: string; sub_agents?: Array<Record<string, unknown>>; flow?: Array<Record<string, unknown>> }>('/info/workflow/current'),

  getLatestWorkflow: (limit: number = 5) =>
    api.get<{ runs: Array<Record<string, unknown>> }>('/info/workflow/latest', { params: { limit } }),

  getThinkingModes: () =>
    api.get<{ modes: Array<{ value: string; name: string; description: string }> }>('/info/thinking/modes'),

  getThoughtProcess: (sessionId: string) =>
    api.get<{ session_id: string; steps: Array<{ id: string; type: string; description: string; status: string; duration_ms: number | null; result: string | null }>; is_complete: boolean; total_duration_ms: number }>(`/info/thoughts/${sessionId}`),

  setThinkingConfig: (config: { mode?: string; enable_tracking?: boolean }) =>
    api.post<{ status: string; mode?: string; enable_tracking?: boolean }>('/info/thinking/config', config),

  // Agent Team API - for canvas visualization (with project support)
  getAgentTeam: (projectId?: string) =>
    api.get<{ agents: Agent[]; active_sub_agents: Record<string, unknown>; current_task: { active: boolean; input: string | null; status: string | null } }>('/info/agent-team', { params: { project_id: projectId } }),

  getAgentDetails: (agentId: string, projectId?: string) =>
    api.get<{ agent_id: string; name: string; description: string; role: string; soul: string; skill: string; memory: string; current_task: { task: string; status: string; type: string } | null; sub_agents: Array<{ agent_id: string; agent_type: string; status: string; input: string }>; status: string; project_id?: string }>(`/info/agent/${agentId}/details`, { params: { project_id: projectId } }),

  getLoadedDocs: (agentId: string) =>
    api.get<{ agent_id: string; loaded_docs: Record<string, { content: string; attributes: Record<string, unknown> }>; doc_count: number }>(`/info/agent/${agentId}/loaded-docs`),

  getInteractions: (limit: number = 20) =>
    api.get<{ interactions: Array<{ run_id: string; source: string; target: string; type: string; task: string; status: string; timestamp: number }> }>('/info/interactions', { params: { limit } }),
};

// Projects API
export const projectsApi = {
  list: () =>
    api.get<{ projects: Project[] }>('/projects'),

  get: (projectId: string) =>
    api.get<ProjectDetails>(`/projects/${projectId}`),

  create: (name: string, description: string = '', project_id: string = '') =>
    api.post<{ status: string; project_id: string; message: string }>('/projects', { name, description, project_id }),

  delete: (projectId: string) =>
    api.delete<{ status: string; message: string }>(`/projects/${projectId}`),

  getAgents: (projectId: string) =>
    api.get<{ agents: Agent[] }>(`/projects/${projectId}/agents`),
};

// Token Usage API
export const tokenUsageApi = {
  getAll: () =>
    api.get<{ all_usage: AllAgentsTokenUsage }>('/token-usage'),

  get: (agentId: string) =>
    api.get<TokenUsageDetails>(`/token-usage/${agentId}`),

  reset: (agentId: string) =>
    api.post<{ status: string; message: string }>(`/token-usage/${agentId}/reset`),
};

export default api;
