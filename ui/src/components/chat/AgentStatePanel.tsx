import { useEffect, useState } from 'react';
import {
  Brain,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Play,
  Clock,
  Activity
} from 'lucide-react';

interface AgentState {
  agent_id: string;
  status: 'idle' | 'received' | 'deciding' | 'thinking' | 'executing' | 'completed' | 'error';
  current_action: string | null;
  route: string | null;
  elapsed_ms: number;
  last_updated: number | null;
  details?: any;
}

interface AgentStatePanelProps {
  agentId: string;
}

const statusConfig: Record<string, { label: string; color: string; icon: any }> = {
  idle: { label: '空闲', color: 'text-gray-500', icon: Clock },
  received: { label: '已接收', color: 'text-blue-500', icon: Play },
  deciding: { label: '决策中', color: 'text-yellow-500', icon: Brain },
  thinking: { label: '思考中', color: 'text-purple-500', icon: Brain },
  executing: { label: '执行中', color: 'text-blue-500', icon: Activity },
  completed: { label: '完成', color: 'text-green-500', icon: CheckCircle2 },
  error: { label: '错误', color: 'text-red-500', icon: AlertCircle },
};

const routeIcons: Record<string, any> = {
  bash: Activity,
  response: Brain,
  memory: Clock,
  heart: Activity,
  chat: Brain,
  create_user: Play,
};

export function AgentStatePanel({ agentId }: AgentStatePanelProps) {
  const [state, setState] = useState<AgentState | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchState = async () => {
    try {
      const res = await fetch(`/api/v1/agent/state/${agentId}`);
      const data = await res.json();
      setState(data.state);
    } catch (err) {
      console.error('Failed to fetch agent state:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 500); // Poll every 500ms
    return () => clearInterval(interval);
  }, [agentId]);

  if (loading || !state) {
    return (
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>加载状态...</span>
        </div>
      </div>
    );
  }

  const config = statusConfig[state.status] || statusConfig.idle;
  const StatusIcon = config.icon;

  // Get route icon
  const RouteIcon = state.route ? routeIcons[state.route] || Activity : Activity;

  // Format elapsed time
  const formatElapsed = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="p-4 border-t border-gray-200 bg-gray-50">
      <div className="space-y-3">
        {/* Status Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StatusIcon className={`w-4 h-4 ${config.color}`} />
            <span className={`text-sm font-medium ${config.color}`}>
              {config.label}
            </span>
          </div>
          {state.elapsed_ms > 0 && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              <span>{formatElapsed(state.elapsed_ms)}</span>
            </div>
          )}
        </div>

        {/* Current Action */}
        {state.current_action && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="text-gray-400">动作:</span>
            <span>{state.current_action}</span>
          </div>
        )}

        {/* Route */}
        {state.route && state.route !== 'uncertain' && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">路由:</span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
              state.route === 'bash' ? 'bg-blue-100 text-blue-700' :
              state.route === 'response' ? 'bg-purple-100 text-purple-700' :
              state.route === 'memory' ? 'bg-green-100 text-green-700' :
              state.route === 'heart' ? 'bg-orange-100 text-orange-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              <RouteIcon className="w-3 h-3" />
              {state.route}
            </span>
          </div>
        )}

        {/* Progress Bar */}
        {state.status === 'executing' || state.status === 'thinking' ? (
          <div className="relative h-1 bg-gray-200 rounded-full overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 animate-pulse rounded-full" />
          </div>
        ) : null}

        {/* Details */}
        {state.details && Object.keys(state.details).length > 0 && (
          <div className="text-xs text-gray-500 bg-white rounded-lg p-2 border border-gray-200">
            {Object.entries(state.details).slice(0, 3).map(([key, value]) => (
              <div key={key} className="flex gap-1">
                <span className="font-medium">{key}:</span>
                <span className="truncate">{String(value).slice(0, 50)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
