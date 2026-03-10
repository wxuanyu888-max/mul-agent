import { useEffect, useState, useCallback, useMemo, memo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  getBezierPath,
  type Node,
  type Edge,
  type NodeProps,
  type EdgeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Brain,
  Bot,
  User,
  Play,
  Pause,
  RefreshCw,
  X,
  FileText,
  Activity,
  Clock,
  Terminal,
  MessageSquare,
  Heart,
  Database,
  Sparkles,
  Loader2,
  ChevronRight,
  BookOpen,
  Zap,
} from 'lucide-react';
import { infoApi, logsApi } from '../../services/api';
import { ProjectSwitcher } from '../project/ProjectSwitcher';
import type { Interaction, InteractionHistoryModalProps } from '../../types';

// Apple 风格节点颜色
const nodeColors = {
  brain: { bg: '#e8f4ff', border: '#0071e3', text: '#0071e3' },
  agent: { bg: '#f5f3ff', border: '#5e5ce6', text: '#5e5ce6' },
  subAgent: { bg: '#f0fdf4', border: '#34c759', text: '#2d7a38' },
  user: { bg: '#fff0f7', border: '#ff2d55', text: '#c91f45' },
  bash: { bg: '#fef3c7', border: '#f59e0b', text: '#b45309' },
  chat: { bg: '#dbeafe', border: '#3b82f6', text: '#1d4ed8' },
  memory: { bg: '#fce7f3', border: '#ec4899', text: '#be185d' },
  heart: { bg: '#e0e7ff', border: '#6366f1', text: '#3730a3' },
  create_user: { bg: '#d1fae5', border: '#10b981', text: '#047857' },
};

// 路由类型到图标和颜色的映射
const routeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  bash: Terminal,
  chat: MessageSquare,
  memory: Database,
  heart: Heart,
  create_user: Sparkles,
  response: Bot,
};

interface NodeData {
  label: string;
  type: string;
  description?: string;
  status?: string;
  agentType?: string;
  agentId?: string;
  icon?: React.ComponentType<{ className?: string }>;
  currentWork?: string;
  loadedDocs?: string[];
  [key: string]: unknown;
}

type CustomNode = Node<NodeData>;
type CustomEdge = Edge<{ label?: string; type?: string } & Record<string, unknown>>;

// 自定义节点组件 - 使用 memo 优化性能
const CustomNodeComponent = memo(function CustomNode({ data, selected }: NodeProps<CustomNode>) {
  const nodeData = data as unknown as NodeData;
  const color = nodeColors[nodeData.type as keyof typeof nodeColors] || nodeColors.agent;
  const Icon = nodeData.icon || Bot;

  // 状态指示器
  const statusColors: Record<string, string> = {
    running: 'bg-green-500 animate-pulse',
    pending: 'bg-amber-400',
    completed: 'bg-blue-500',
    failed: 'bg-red-500',
    idle: 'bg-gray-400',
    working: 'bg-green-500 animate-pulse',
    thinking: 'bg-yellow-500 animate-pulse',
    executing: 'bg-blue-500 animate-pulse',
  };

  // 根据节点类型选择图标
  const TypeIcon = nodeData.type === 'bash' ? Terminal
    : nodeData.type === 'chat' ? MessageSquare
    : nodeData.type === 'memory' ? Database
    : nodeData.type === 'heart' ? Heart
    : nodeData.type === 'create_user' ? Sparkles
    : Icon;

  return (
    <div
      className={`px-4 py-3 rounded-xl shadow-lg border-2 transition-all duration-200 bg-white cursor-pointer hover:shadow-xl ${
        selected ? 'ring-2 ring-blue-500 scale-105' : ''
      }`}
      style={{
        borderColor: color.border,
        minWidth: '180px',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-300 !border-2 !border-white"
      />
      <div className="flex items-center gap-2.5">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: color.bg }}
        >
          {TypeIcon && <TypeIcon className="w-4 h-4" style={{ color: color.text }} />}
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-gray-900 font-semibold text-sm block truncate">{nodeData.label}</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className={`w-2 h-2 rounded-full ${statusColors[nodeData.status || 'idle']}`} />
            <span className="text-gray-500 text-xs capitalize truncate">{nodeData.status || 'idle'}</span>
          </div>
        </div>
      </div>
      {nodeData.agentType && (
        <div className="flex items-center gap-1 mt-1.5 ml-11">
          <Zap className="w-3 h-3 text-gray-400" />
          <span className="text-gray-500 text-xs font-mono truncate max-w-[120px]">{nodeData.agentType}</span>
        </div>
      )}
      {nodeData.description && (
        <p className="text-gray-400 text-xs mt-1 ml-11 truncate max-w-[150px]">{nodeData.description}</p>
      )}
      {nodeData.currentWork && (
        <div className="mt-2 ml-11 p-1.5 bg-blue-50 rounded border border-blue-100">
          <p className="text-blue-700 text-xs font-medium">Working:</p>
          <p className="text-blue-600 text-xs truncate">{nodeData.currentWork}</p>
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-300 !border-2 !border-white"
      />
    </div>
  );
});

// 自定义边组件 - 使用 memo 优化性能
const CustomEdgeComponent = memo(function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  data,
  markerEnd,
  onClick,
}: EdgeProps<CustomEdge> & { onClick?: () => void }) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeData = data as unknown as { label?: string; type?: string; status?: string; source?: string; target?: string };

  // 获取 source 和 target（从 edge data 或 style 中获取）
  const source = edgeData?.source || '';
  const target = edgeData?.target || '';

  // 根据交互类型设置颜色
  const strokeColors: Record<string, string> = {
    chat: '#5e5ce6',
    bash: '#ff9500',
    create_user: '#34c759',
    memory: '#ff2d55',
    heart: '#0071e3',
    collaboration: '#a855f7',
    delegation: '#0071e3',
    default: '#d2d2d7',
  };

  const strokeColor = edgeData?.type ? (strokeColors[edgeData.type] || strokeColors.default) : strokeColors.default;

  // 判断是否是活跃交互（executing 状态）
  const isActive = edgeData?.status === 'executing' || edgeData?.status === 'active';

  // 脉冲动画样式
  const pulseAnimation = isActive ? 'pulse 1.5s ease-in-out infinite' : 'none';

  return (
    <>
      <path
        id={id}
        style={{
          ...style,
          strokeWidth: style.strokeWidth || 2,
          stroke: strokeColor,
          fill: 'none',
          strokeDasharray: edgeData?.type && edgeData.type !== 'collaboration' ? '5,5' : 'none',
          animation: edgeData?.type ? pulseAnimation : 'none',
          cursor: onClick ? 'pointer' : 'default',
        }}
        d={edgePath}
        markerEnd={markerEnd}
        onClick={onClick}
      />
      {edgeData?.label && (
        <g onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
          <rect
            x={(sourceX + targetX) / 2 - 35}
            y={(sourceY + targetY) / 2 - 12}
            width={70}
            height={24}
            fill="white"
            rx={6}
            stroke={strokeColor}
            strokeWidth={1}
          />
          <text
            x={(sourceX + targetX) / 2}
            y={(sourceY + targetY) / 2 + 4}
            style={{
              fontSize: '10px',
              fill: strokeColor,
              textAnchor: 'middle',
              fontWeight: 600,
            }}
          >
            {edgeData.label}
          </text>
        </g>
      )}
    </>
  );
});

// Memoized node and edge types
const nodeTypesMemo = { custom: CustomNodeComponent };
const edgeTypesMemo = { custom: CustomEdgeComponent };

interface Agent {
  agent_id: string;
  name: string;
  description: string;
  role: string | Record<string, unknown>;
  status?: string;
}

interface AgentDetailsModalProps {
  agentId: string;
  agentType?: string;
  projectId?: string;
  onClose: () => void;
}

// Agent 详情弹窗组件 - 显示加载的文档和正在干的工作
function AgentDetailsModal({ agentId, agentType, projectId, onClose }: AgentDetailsModalProps) {
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'soul' | 'role' | 'skill' | 'memory' | 'work' | 'logs'>('soul');
  const [logs, setLogs] = useState<any[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        const res = await infoApi.getAgentDetails(agentId, projectId);
        setDetails(res.data);
      } catch (error) {
        console.error('Failed to fetch agent details:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [agentId, projectId]);

  // 获取 agent 相关日志
  useEffect(() => {
    if (activeTab === 'logs') {
      setLoadingLogs(true);
      logsApi.getLogs(50, undefined, agentId).then((res) => {
        setLogs(res.data.logs || []);
        setLoadingLogs(false);
      }).catch(() => {
        setLoadingLogs(false);
      });
    }
  }, [activeTab, agentId]);

  const tabs = [
    { id: 'soul', label: 'Soul', icon: FileText },
    { id: 'role', label: 'Role', icon: User },
    { id: 'skill', label: 'Skill', icon: Activity },
    { id: 'memory', label: 'Memory', icon: Clock },
    { id: 'work', label: 'Current Work', icon: Play },
    { id: 'logs', label: 'Logs', icon: BookOpen },
  ];

  // 渲染当前工作面板
  const renderWorkPanel = () => {
    if (!details?.current_task) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Bot className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No active task</p>
          <p className="text-sm mt-1">This agent is currently idle</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* 任务状态 */}
        <div className={`p-4 rounded-xl border-2 ${
          details.current_task.status === 'running'
            ? 'border-green-200 bg-green-50'
            : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            {details.current_task.status === 'running' ? (
              <Loader2 className="w-5 h-5 text-green-600 animate-spin" />
            ) : (
              <Play className="w-5 h-5 text-gray-500" />
            )}
            <span className="font-semibold text-gray-900">Current Task</span>
            <span className={`ml-auto text-xs font-medium px-2 py-1 rounded-full ${
              details.current_task.status === 'running'
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-600'
            }`}>
              {details.current_task.status}
            </span>
          </div>
          <p className="text-gray-700 font-mono text-sm bg-white p-3 rounded border border-gray-200">
            {details.current_task.task}
          </p>
        </div>

        {/* 加载的文档 */}
        <div className="p-4 rounded-xl border border-gray-200 bg-white">
          <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-blue-500" />
            Loaded Documents
          </h4>
          <div className="space-y-2">
            {['soul', 'user', 'skill', 'memory'].map((docType) => (
              <button
                key={docType}
                onClick={() => setActiveTab(docType as typeof activeTab)}
                className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 border border-gray-100 transition-colors"
              >
                <FileText className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-700 capitalize">{docType}.md</span>
                <ChevronRight className="w-4 h-4 text-gray-300 ml-auto" />
              </button>
            ))}
          </div>
        </div>

        {/* 子 Agent 信息 */}
        {details.sub_agents && details.sub_agents.length > 0 && (
          <div className="p-4 rounded-xl border border-purple-200 bg-purple-50">
            <h4 className="font-semibold text-purple-900 mb-3 flex items-center gap-2">
              <Bot className="w-4 h-4 text-purple-500" />
              Delegated Sub-Agents ({details.sub_agents.length})
            </h4>
            <div className="space-y-2">
              {details.sub_agents.map((sa: any, i: number) => (
                <div key={i} className="flex items-center gap-2 p-2 bg-white rounded border border-purple-100">
                  <span className="w-2 h-2 rounded-full bg-purple-500" />
                  <span className="text-sm text-gray-700 font-mono flex-1">{sa.agent_id}</span>
                  <span className="text-xs text-gray-500 px-2 py-1 bg-gray-100 rounded">{sa.agent_type}</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    sa.status === 'completed' ? 'bg-green-100 text-green-700' :
                    sa.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{sa.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // 渲染日志面板
  const renderLogsPanel = () => {
    if (loadingLogs) {
      return (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
        </div>
      );
    }

    if (logs.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <BookOpen className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No logs found</p>
        </div>
      );
    }

    return (
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {logs.map((log, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg border text-xs font-mono ${
              log.level === 'ERROR'
                ? 'border-red-200 bg-red-50 text-red-700'
                : log.level === 'WARNING'
                ? 'border-amber-200 bg-amber-50 text-amber-700'
                : 'border-gray-200 bg-gray-50 text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-gray-500">{log.datetime || new Date().toISOString()}</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${
                log.level === 'ERROR' ? 'bg-red-100 text-red-700' :
                log.level === 'WARNING' ? 'bg-amber-100 text-amber-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {log.level || 'INFO'}
              </span>
              <span className="text-blue-600 font-semibold">{log.source}</span>
            </div>
            <p className="whitespace-pre-wrap">{log.message}</p>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-100 to-purple-200 flex items-center justify-center">
              <Bot className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{details?.name || agentId}</h2>
              <p className="text-sm text-gray-500">{details?.description || agentType || 'Agent'}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Status Bar */}
        {details?.current_task && (
          <div className="px-6 py-3 bg-green-50 border-b border-green-100">
            <div className="flex items-center gap-2">
              <Play className="w-4 h-4 text-green-600 animate-pulse" />
              <span className="text-sm font-medium text-green-800">Working:</span>
              <span className="text-sm text-green-700 truncate flex-1">{details.current_task.task}</span>
              <span className="text-xs text-green-600 font-medium px-2 py-1 rounded-full bg-green-100 capitalize">
                {details.current_task.status}
              </span>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-6 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-purple-500 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          ) : activeTab === 'work' ? (
            renderWorkPanel()
          ) : activeTab === 'logs' ? (
            renderLogsPanel()
          ) : (
            <div className="prose prose-sm max-w-none">
              <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs bg-gray-50 p-4 rounded-lg overflow-x-auto">
                {details?.[activeTab] || 'No content available'}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Agent ID: {agentId}</span>
            <span>Type: {agentType || 'standard'}</span>
            <span>Status: {details?.status || 'idle'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// 初始节点
const getInitialNodes = (agentTeam?: Agent[], project_id?: string): CustomNode[] => {
  const nodes: CustomNode[] = [
    {
      id: 'user',
      type: 'custom',
      position: { x: 350, y: 30 },
      data: {
        label: 'User',
        type: 'user',
        description: 'You',
        icon: User,
        status: 'idle',
      },
    },
    {
      id: 'core-brain',
      type: 'custom',
      position: { x: 350, y: 150 },
      data: {
        label: 'Core Brain',
        type: 'brain',
        description: 'Central Coordinator',
        icon: Brain,
        status: 'idle',
      },
    },
  ];

  // 如果有 agent team，添加每个 agent 作为节点
  if (agentTeam && agentTeam.length > 0) {
    const agentNodes: CustomNode[] = agentTeam.map((agent, index) => {
      // 根据 agent 类型选择图标
      let agentIcon = Bot;
      let nodeType = 'agent';

      if (agent.name?.toLowerCase().includes('coder') || agent.description?.toLowerCase().includes('code')) {
        agentIcon = Terminal;
        nodeType = 'bash';
      } else if (agent.name?.toLowerCase().includes('writer')) {
        agentIcon = FileText;
        nodeType = 'chat';
      } else if (agent.name?.toLowerCase().includes('researcher')) {
        agentIcon = BookOpen;
        nodeType = 'chat';
      }

      return {
        id: `agent-${agent.agent_id}`,
        type: 'custom',
        position: {
          x: 150 + (index % 2) * 400,
          y: 300 + Math.floor(index / 2) * 120
        },
        data: {
          label: agent.name || agent.agent_id,
          type: nodeType,
          description: agent.description || 'Team Member',
          agentId: agent.agent_id,
          icon: agentIcon,
          status: 'idle',
          project_id: (agent as any).project_id || project_id,
        },
      };
    });
    nodes.push(...agentNodes);
  }

  return nodes;
};

// 初始边
const getInitialEdges = (agentTeam?: Agent[]): CustomEdge[] => {
  const edges: CustomEdge[] = [
    { id: 'e-user-brain', source: 'user', target: 'core-brain', type: 'custom' },
  ];

  // 注意：不在这里创建 brain 到 agent 的边，由 fetchInteractions 统一处理
  // 这样可以根据是否有交互数据来显示不同样式的连线

  return edges;
};

export function WorkflowCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<CustomNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<CustomEdge>([]);
  const [isActive, setIsActive] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<string>('idle');
  const [subAgents, setSubAgents] = useState<Array<Record<string, unknown>>>([]);
  const [agentTeam, setAgentTeam] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<{ agentId: string; agentType?: string; projectId?: string } | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [interactions, setInteractions] = useState<Array<{ run_id: string; source: string; target: string; type: string; task: string; status: string; timestamp: number }>>([]);

  // 获取工作流状态
  const fetchWorkflowStatus = useCallback(async () => {
    try {
      const currentRes = await infoApi.getCurrentWorkflow();
      const currentData = currentRes.data;
      setIsActive(currentData.active);

      if (currentData.active) {
        setCurrentPhase(currentData.phase || 'running');
        setSubAgents(currentData.sub_agents || []);

        // 更新节点状态 - 使用函数式更新避免依赖问题
        setNodes((nds) => {
          // 先过滤掉旧的 sub-agent 节点
          const filteredNodes = nds.filter((n) => !n.id.startsWith('sub-'));

          // 更新 core-brain 状态
          const updatedNodes = filteredNodes.map((node) => {
            if (node.id === 'core-brain') {
              return {
                ...node,
                data: {
                  ...node.data,
                  status: currentData.phase || 'running',
                  description: currentData.phase || 'Processing',
                },
              };
            }
            return node;
          });

          // 添加新的 sub-agent 节点
          const subAgentNodes: CustomNode[] = (currentData.sub_agents || []).map((sa: Record<string, unknown>, index: number) => ({
            id: `sub-${sa.agent_id}`,
            type: 'custom',
            position: { x: 100 + (index % 3) * 200, y: 420 + Math.floor(index / 3) * 100 },
            data: {
              label: (sa.agent_id as string) || `Agent ${index + 1}`,
              type: (sa.agent_type as string) || 'subAgent',
              agentType: sa.agent_type as string,
              status: (sa.status as string) || 'running',
              agentId: sa.agent_id as string,
              currentWork: (sa.input as string) || '',
              icon: routeIcons[sa.agent_type as string] || Bot,
            },
          }));

          return [...updatedNodes, ...subAgentNodes];
        });

        // 更新边
        setEdges((eds) => {
          // 过滤掉旧的 sub-agent 边
          const filteredEdges = eds.filter((e) => !e.id.startsWith('e-team-'));

          // 添加新的 sub-agent 边
          const subAgentEdges: CustomEdge[] = (currentData.sub_agents || []).map((sa: Record<string, unknown>) => {
            const agentType = sa.agent_type as string;
            let source = 'core-brain';

            // 如果是 chat 类型，尝试找到对应的 agent
            if (agentType === 'chat' && sa.target_agent) {
              source = `agent-${sa.target_agent}`;
            }

            return {
              id: `e-team-${sa.agent_id}`,
              source,
              target: `sub-${sa.agent_id}`,
              type: 'custom',
              data: { label: agentType, type: agentType },
            };
          });

          return [...filteredEdges, ...subAgentEdges];
        });

        setError(null);
      } else {
        // 没有活动任务时，重置状态
        setCurrentPhase('idle');
        setSubAgents([]);

        setNodes((nds) => {
          // 过滤掉 sub-agent 节点，保留基础节点
          return nds.filter((n) => !n.id.startsWith('sub-')).map((node) => {
            if (node.id === 'core-brain') {
              return {
                ...node,
                data: { ...node.data, status: 'idle' },
              };
            }
            return node;
          });
        });

        setEdges((eds) => eds.filter((e) => !e.id.startsWith('e-team-')));
      }

      setError(null);
    } catch (err) {
      console.error('Failed to fetch workflow status:', err);
      setError('Failed to fetch workflow status');
    }
  }, [setNodes, setEdges]);

  // 获取 Agent Team 列表
  const fetchAgentTeam = useCallback(async () => {
    try {
      const res = await infoApi.getAgentTeam(selectedProjectId || undefined);
      const agents = res.data.agents || [];
      setAgentTeam(agents);

      // 初始化节点和边 - 重置所有状态
      const initialNodes = getInitialNodes(agents, selectedProjectId || undefined);
      const initialEdges = getInitialEdges(agents);
      setNodes(initialNodes);
      setEdges(initialEdges);

      // 获取交互数据并创建交互边
      const interactionsRes = await infoApi.getInteractions(50);
      const interactionList = interactionsRes.data.interactions || [];
      setInteractions(interactionList);

      // 根据交互创建边 - 只连接到当前显示的 agent
      setEdges((eds) => {
        // 保留现有的基础边（user-brain 和 brain-agent）
        const baseEdges = eds.filter((e) => !e.id.startsWith('e-interaction-'));

        // 从交互数据创建新的边
        const interactionEdges = interactionList
          .filter((interaction) => {
            // 只显示与当前项目 agent 相关的交互
            if (!selectedProjectId) {
              // all-project 模式，显示所有交互
              return true;
            }
            // 特定项目模式，只显示与该项目的 agent 相关的交互
            const isSourceRelated = interaction.source === 'wang' || interaction.source === 'core-brain' || agents.some(a => a.agent_id === interaction.source);
            const isTargetRelated = interaction.target === 'wang' || interaction.target === 'core-brain' || agents.some(a => a.agent_id === interaction.target);
            return isSourceRelated || isTargetRelated;
          })
          .map((interaction, index) => {
            const sourceId = interaction.source === 'wang' || interaction.source === 'core-brain' ? 'core-brain' : `agent-${interaction.source}`;
            const targetId = interaction.target === 'wang' || interaction.target === 'core-brain' ? 'core-brain' : `agent-${interaction.target}`;

            // 检查目标 agent 是否在当前显示的列表中
            const sourceExists = sourceId === 'core-brain' || sourceId === 'user' || agents.some(a => `agent-${a.agent_id}` === sourceId);
            const targetExists = targetId === 'core-brain' || targetId === 'user' || agents.some(a => `agent-${a.agent_id}` === targetId);

            if (!sourceExists || !targetExists) {
              return null;
            }

            return {
              id: `e-interaction-${index}-${interaction.run_id}`,
              source: sourceId,
              target: targetId,
              type: 'custom' as const,
              data: {
                label: interaction.type,
                type: interaction.type,
                task: interaction.task,
              },
              style: {
                stroke: interaction.status === 'executing' ? '#22c55e' : '#6b7280',
                strokeWidth: 3,
              },
            };
          }).filter(Boolean);

        return [...baseEdges, ...interactionEdges] as CustomEdge[];
      });
    } catch (err) {
      console.error('Failed to fetch agent team:', err);
    }
  }, [setNodes, setEdges, selectedProjectId]);

  // 获取交互数据（定时刷新）
  const fetchInteractions = useCallback(async () => {
    try {
      const res = await infoApi.getInteractions(50);
      const interactionList = res.data.interactions || [];
      setInteractions(interactionList);

      // 根据交互创建边 - 只连接到当前显示的 agent
      setEdges((eds) => {
        // 保留现有的基础边（user-brain 和 brain-agent）
        const baseEdges = eds.filter((e) => !e.id.startsWith('e-interaction-'));

        // 如果没有交互数据，就从 agentTeam 创建默认的协作关系边
        if (interactionList.length === 0 && agentTeam.length > 0) {
          // 为每个 agent 创建一条连接到 core-brain 的虚线边，表示团队协作关系
          const teamEdges: CustomEdge[] = agentTeam.map((agent) => ({
            id: `e-team-collab-${agent.agent_id}`,
            source: 'core-brain',
            target: `agent-${agent.agent_id}`,
            type: 'custom',
            data: {
              label: 'collaboration',
              type: 'collaboration',
              task: 'Team collaboration',
              source: 'core_brain',
              target: agent.agent_id,
              status: 'active',
            },
            style: {
              stroke: '#a855f7',
              strokeWidth: 2,
              strokeDasharray: '5,5',
            },
          }));

          return [...baseEdges, ...teamEdges];
        }

        // 从交互数据创建新的边
        const interactionEdges = interactionList
          .filter((interaction) => {
            // 只显示与当前项目 agent 相关的交互
            if (!selectedProjectId) {
              // all-project 模式，显示所有交互
              return true;
            }
            // 特定项目模式，只显示与该项目的 agent 相关的交互
            const isSourceRelated = interaction.source === 'wang' || interaction.source === 'core-brain' || agentTeam.some(a => a.agent_id === interaction.source);
            const isTargetRelated = interaction.target === 'wang' || interaction.target === 'core-brain' || agentTeam.some(a => a.agent_id === interaction.target);
            return isSourceRelated || isTargetRelated;
          })
          .map((interaction, index) => {
            const sourceId = interaction.source === 'wang' || interaction.source === 'core-brain' ? 'core-brain' : `agent-${interaction.source}`;
            const targetId = interaction.target === 'wang' || interaction.target === 'core-brain' ? 'core-brain' : `agent-${interaction.target}`;

            // 检查目标 agent 是否在当前显示的列表中
            const sourceExists = sourceId === 'core-brain' || sourceId === 'user' || agentTeam.some(a => `agent-${a.agent_id}` === sourceId);
            const targetExists = targetId === 'core-brain' || targetId === 'user' || agentTeam.some(a => `agent-${a.agent_id}` === targetId);

            if (!sourceExists || !targetExists) {
              return null;
            }

            return {
              id: `e-interaction-${index}-${interaction.run_id}`,
              source: sourceId,
              target: targetId,
              type: 'custom' as const,
              data: {
                label: interaction.type,
                type: interaction.type,
                task: interaction.task,
                source: interaction.source,
                target: interaction.target,
                status: interaction.status,
              },
              style: {
                stroke: interaction.status === 'executing' ? '#22c55e' : '#6b7280',
                strokeWidth: 3,
              },
            };
          }).filter(Boolean);

        return [...baseEdges, ...interactionEdges] as CustomEdge[];
      });
    } catch (err) {
      console.error('Failed to fetch interactions:', err);
    }
  }, [setEdges, selectedProjectId, agentTeam]);

  // 定时获取工作流状态 - 只获取一次，避免无限循环
  useEffect(() => {
    let mounted = true;

    const fetchStatus = async () => {
      if (!mounted) return;
      await fetchWorkflowStatus();
    };

    fetchStatus();
    const interval = setInterval(() => {
      if (mounted) fetchWorkflowStatus();
    }, 3000); // 每 3 秒刷新一次

    return () => {
      mounted = false;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 获取交互数据
  useEffect(() => {
    let mounted = true;

    const fetchInteractionsData = async () => {
      if (!mounted) return;
      await fetchInteractions();
    };

    fetchInteractionsData();
    const interval = setInterval(() => {
      if (mounted) fetchInteractions();
    }, 5000); // 每 5 秒刷新一次交互数据

    return () => {
      mounted = false;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 获取 Agent Team
  useEffect(() => {
    fetchAgentTeam();
  }, [fetchAgentTeam, selectedProjectId]);

  // 处理项目切换
  const handleProjectChange = useCallback((projectId: string | null) => {
    setSelectedProjectId(projectId);
  }, []);

  // 处理节点点击
  const onNodeClick = useCallback((_: React.MouseEvent, node: CustomNode) => {
    const agentId = node.data.agentId;
    const agentType = node.data.type as string;
    const projectId = node.data.project_id as string | undefined;
    if (agentId) {
      setSelectedAgent({ agentId, agentType, projectId });
    }
  }, []);

  // 交互历史弹窗相关状态
  const [selectedInteraction, setSelectedInteraction] = useState<{ source: string; target: string } | null>(null);
  const [interactionHistory, setInteractionHistory] = useState<Interaction[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // 处理边点击 - 显示交互历史
  const onEdgeClick = useCallback((_: React.MouseEvent, edge: CustomEdge) => {
    const source = edge.data?.source as string || '';
    const target = edge.data?.target as string || '';
    if (source && target) {
      setSelectedInteraction({ source, target });
      setLoadingHistory(true);
      // 获取这两个 agent 之间的交互历史（5 分钟内）
      infoApi.getAgentInteractions(source, target, 300, 50).then((res) => {
        setInteractionHistory(res.data.interactions || []);
        setLoadingHistory(false);
      }).catch(() => {
        setInteractionHistory([]);
        setLoadingHistory(false);
      });
    }
  }, []);

  // Performance optimized ReactFlow config
  const flowOptions = useMemo(() => ({
    nodeOrigin: [0.5, 0] as [number, number],
    selectNodesOnDrag: false,
    snapToGrid: true,
    snapGrid: [15, 15] as [number, number],
    minZoom: 0.5,
    maxZoom: 1.5,
    fitView: true,
    fitViewOptions: { padding: 0.2 },
    nodesConnectable: false,
    nodesDraggable: false,
    panOnDrag: true,
    zoomOnScroll: true,
    zoomOnPinch: true,
    zoomOnDoubleClick: false,
    preventScrolling: true,
    onNodeClick,
    onEdgeClick,
  }), [onNodeClick, onEdgeClick]);

  return (
    <div className="w-full h-full bg-gray-50 relative overflow-hidden">
      {/* Header */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        {/* Project Switcher */}
        <ProjectSwitcher
          selectedProjectId={selectedProjectId || undefined}
          onProjectChange={handleProjectChange}
        />

        {/* Workflow Status */}
        <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 p-4 shadow-lg min-w-[200px]">
          <div className="flex items-center gap-2 mb-2">
            {isActive ? (
              <Pause className="w-4 h-4 text-green-500 animate-pulse" />
            ) : (
              <Play className="w-4 h-4 text-gray-400" />
            )}
            <h2 className="text-base font-semibold text-gray-900">Workflow Status</h2>
          </div>
          <div className="space-y-1.5 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Status:</span>
              <span className={`font-medium ${isActive ? 'text-green-600' : 'text-gray-400'}`}>
                {isActive ? 'Running' : 'Idle'}
              </span>
            </div>
            {isActive && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Phase:</span>
                  <span className="font-medium text-gray-700">{currentPhase}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Sub-agents:</span>
                  <span className="font-medium text-gray-700">{subAgents.length}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="absolute top-4 right-4 z-10 bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 p-3 shadow-lg">
        <h3 className="text-xs font-semibold text-gray-700 mb-2">Legend</h3>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-blue-500" style={{ backgroundColor: nodeColors.brain.border }} />
            <span className="text-gray-600">Core Brain</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-purple-500" style={{ backgroundColor: nodeColors.agent.border }} />
            <span className="text-gray-600">Agent Team</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-green-500" style={{ backgroundColor: nodeColors.subAgent.border }} />
            <span className="text-gray-600">Sub-Agent</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-yellow-500" style={{ backgroundColor: nodeColors.bash.border }} />
            <span className="text-gray-600">Bash Executor</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-blue-400" style={{ backgroundColor: nodeColors.chat.border }} />
            <span className="text-gray-600">Chat Agent</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-pink-400" style={{ backgroundColor: nodeColors.memory.border }} />
            <span className="text-gray-600">Memory Agent</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-pink-500" style={{ backgroundColor: nodeColors.user.border }} />
            <span className="text-gray-600">User</span>
          </div>
          <div className="border-t border-gray-200 my-1.5" />
          <div className="flex items-center gap-2">
            <span className="w-6 h-0.5 bg-green-500" />
            <span className="text-gray-600">Active Interaction</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-0.5 bg-gray-400" />
            <span className="text-gray-600">Past Interaction</span>
          </div>
        </div>
      </div>

      {/* Agent Team Count */}
      <div className="absolute top-36 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 p-3 shadow-lg">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-purple-500" />
          <span className="text-sm font-medium text-gray-700">Agents: {agentTeam.length}</span>
        </div>
      </div>

      {/* Interactions Count */}
      <div className="absolute top-44 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 p-3 shadow-lg">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-green-500" />
          <span className="text-sm font-medium text-gray-700">Interactions: {interactions.length}</span>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* ReactFlow Canvas */}
      <div className="w-full h-full absolute inset-0">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypesMemo}
          edgeTypes={edgeTypesMemo}
          {...flowOptions}
          className="w-full h-full bg-gray-50"
        >
          <Background
            color="#e5e5e7"
            gap={24}
            size={1}
          />
          <Controls
            className="bg-white border-gray-200 shadow-lg rounded-lg"
            showInteractive={false}
          />
        </ReactFlow>
      </div>

      {/* Refresh Button */}
      <button
        onClick={fetchWorkflowStatus}
        className="absolute bottom-4 right-4 z-10 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg p-2 shadow-lg transition-colors"
        title="Refresh workflow status"
      >
        <RefreshCw className="w-5 h-5 text-gray-600" />
      </button>

      {/* Agent Details Modal */}
      {selectedAgent && (
        <AgentDetailsModal
          agentId={selectedAgent.agentId}
          agentType={selectedAgent.agentType}
          projectId={(selectedAgent as any).projectId}
          onClose={() => setSelectedAgent(null)}
        />
      )}

      {/* Interaction History Modal */}
      {selectedInteraction && (
        <InteractionHistoryModal
          source={selectedInteraction.source}
          target={selectedInteraction.target}
          onClose={() => setSelectedInteraction(null)}
        />
      )}

      {/* Add CSS animation for edge */}
      <style>{`
        @keyframes dashAnimation {
          to {
            stroke-dashoffset: -10;
          }
        }

        @keyframes pulse {
          0%, 100% {
            stroke-opacity: 1;
            stroke-width: 3;
          }
          50% {
            stroke-opacity: 0.5;
            stroke-width: 2;
          }
        }
      `}</style>
    </div>
  );
}


// Interaction History Modal Component
function InteractionHistoryModal({ source, target, onClose }: InteractionHistoryModalProps) {
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    // Get interactions between source and target (5 minutes window)
    infoApi.getAgentInteractions(source, target, 300, 50).then((res) => {
      setInteractions(res.data.interactions || []);
      setLoading(false);
    }).catch(() => {
      setInteractions([]);
      setLoading(false);
    });
  }, [source, target]);

  // Format timestamp to readable time
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
  };

  // Get type icon
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'bash': return Terminal;
      case 'chat': return MessageSquare;
      case 'memory': return Database;
      case 'heart': return Heart;
      case 'delegation': return Zap;
      case 'collaboration': return Bot;
      default: return Bot;
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'executing': return 'bg-green-100 text-green-700';
      case 'active': return 'bg-green-100 text-green-700';
      case 'pending': return 'bg-amber-100 text-amber-700';
      case 'completed': return 'bg-blue-100 text-blue-700';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-100 to-purple-200 flex items-center justify-center">
              <Activity className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Interaction History</h2>
              <p className="text-sm text-gray-500">{source} → {target}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          ) : interactions.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No interactions found in the last 5 minutes</p>
            </div>
          ) : (
            <div className="space-y-2">
              {interactions.map((interaction, index) => {
                const TypeIcon = getTypeIcon(interaction.type);
                return (
                  <div
                    key={index}
                    className="p-3 rounded-lg border border-gray-200 hover:border-purple-300 transition-colors"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <TypeIcon className="w-4 h-4 text-gray-400" />
                      <span className="text-xs font-medium text-gray-500 capitalize">{interaction.type}</span>
                      <span className="text-xs text-gray-400 ml-auto">{formatTime(interaction.timestamp)}</span>
                    </div>
                    <p className="text-sm text-gray-700 truncate">{interaction.task || 'No task description'}</p>
                    <div className="mt-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(interaction.status)}`}>
                        {interaction.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Showing last 5 minutes</span>
            <span>{interactions.length} interaction(s)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
