import { useState, useEffect } from 'react';
import {
  Database,
  RefreshCw,
  Trash2,
  Plus,
  Clock,
  FileText,
  Brain,
  HardDrive,
  ArrowRightLeft,
} from 'lucide-react';
import { memoryApi } from '../../services/api';

interface Memory {
  id: string;
  content: string;
  timestamp: string | number;
  type: string;
  agent_id?: string;
  from_agent?: string;
  to_agent?: string;
  status?: string;
}

type MemoryType = 'short' | 'long' | 'handover';

export function MemoryPanel() {
  const [shortTermMemories, setShortTermMemories] = useState<Memory[]>([]);
  const [longTermMemories, setLongTermMemories] = useState<Memory[]>([]);
  const [handoverMemories, setHandoverMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeType, setActiveType] = useState<MemoryType>('short');
  const [newMemory, setNewMemory] = useState('');
  const [agentId, setAgentId] = useState('core_brain');

  const fetchMemories = async () => {
    setLoading(true);
    try {
      const [shortRes, longRes, handoverRes] = await Promise.all([
        memoryApi.getShortTerm(agentId, 50),
        memoryApi.getLongTerm(agentId, 50),
        memoryApi.getHandover(agentId),
      ]);

      setShortTermMemories(shortRes.data?.memories || []);
      setLongTermMemories(longRes.data?.memories || []);
      setHandoverMemories(handoverRes.data?.memories || []);
    } catch (err) {
      console.error('Failed to fetch memories:', err);
      // Set empty arrays on error to avoid undefined state
      setShortTermMemories([]);
      setLongTermMemories([]);
      setHandoverMemories([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
    const interval = setInterval(fetchMemories, 10000);
    return () => clearInterval(interval);
  }, [agentId]);

  const writeMemory = async () => {
    if (!newMemory.trim()) return;

    try {
      await memoryApi.write(
        newMemory,
        agentId,
        activeType === 'short' ? 'short_term' : 'long_term'
      );
      setNewMemory('');
      fetchMemories();
    } catch (err) {
      console.error('Failed to write memory:', err);
    }
  };

  const deleteMemory = async (memoryId: string) => {
    try {
      await memoryApi.delete(
        memoryId,
        agentId,
        activeType === 'short' ? 'short_term' : 'long_term'
      );
      fetchMemories();
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  const getMemories = () => {
    switch (activeType) {
      case 'short':
        return shortTermMemories;
      case 'long':
        return longTermMemories;
      case 'handover':
        return handoverMemories;
    }
  };

  const getTypeIcon = (type: MemoryType) => {
    switch (type) {
      case 'short':
        return Brain;
      case 'long':
        return HardDrive;
      case 'handover':
        return ArrowRightLeft;
    }
  };

  const getTypeLabel = (type: MemoryType) => {
    switch (type) {
      case 'short':
        return 'Short-term';
      case 'long':
        return 'Long-term';
      case 'handover':
        return 'Handover';
    }
  };

  const getTypeCount = (type: MemoryType) => {
    switch (type) {
      case 'short':
        return shortTermMemories.length;
      case 'long':
        return longTermMemories.length;
      case 'handover':
        return handoverMemories.length;
    }
  };

  const memories = getMemories();

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-100 to-pink-200 flex items-center justify-center">
              <Database className="w-5 h-5 text-pink-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Memory</h2>
              <p className="text-sm text-gray-500">
                {getTypeCount(activeType)} memories in {getTypeLabel(activeType).toLowerCase()} storage
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Agent Selector */}
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500"
            >
              <option value="core_brain">Core Brain</option>
              <option value="my_clone">My Clone</option>
            </select>

            {/* Refresh Button */}
            <button
              onClick={fetchMemories}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Memory Type Tabs */}
        <div className="flex gap-2">
          {(['short', 'long', 'handover'] as MemoryType[]).map((type) => {
            const Icon = getTypeIcon(type);
            return (
              <button
                key={type}
                onClick={() => setActiveType(type)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  activeType === type
                    ? 'bg-pink-100 text-pink-700'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-4 h-4" />
                {getTypeLabel(type)}
                <span className="bg-white/50 px-2 py-0.5 rounded-full text-xs">
                  {getTypeCount(type)}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Write Memory */}
      {(activeType === 'short' || activeType === 'long') && (
        <div className="px-6 py-4 border-b border-gray-100 bg-pink-50">
          <div className="flex items-start gap-3">
            <Plus className="w-5 h-5 text-pink-600 mt-1" />
            <div className="flex-1">
              <textarea
                value={newMemory}
                onChange={(e) => setNewMemory(e.target.value)}
                placeholder={`Add new ${getTypeLabel(activeType).toLowerCase()} memory...`}
                rows={2}
                className="w-full resize-none bg-white border border-pink-200 rounded-xl px-4 py-3 text-gray-700 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500"
              />
              <button
                onClick={writeMemory}
                disabled={!newMemory.trim()}
                className="mt-2 px-4 py-2 bg-pink-600 hover:bg-pink-700 disabled:bg-gray-300 text-white rounded-lg font-medium text-sm transition-all disabled:cursor-not-allowed"
              >
                Add Memory
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Memories List */}
      <div className="flex-1 overflow-y-auto px-6 py-4 bg-gray-50">
        {loading && memories.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-8 h-8 text-gray-400 animate-spin" />
          </div>
        ) : memories.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Database className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-medium">No memories</p>
            <p className="text-sm mt-1">
              {activeType === 'short' || activeType === 'long'
                ? 'Add a new memory to get started'
                : 'No handover memories available'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {memories.map((memory, index) => (
              <div
                key={memory.id || index}
                className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-4 h-4 text-pink-500" />
                      <span className="text-xs font-medium text-pink-600 uppercase">
                        {memory.type || activeType}
                      </span>
                      {memory.timestamp && (
                        <div className="flex items-center gap-1 text-gray-400">
                          <Clock className="w-3 h-3" />
                          <span className="text-xs">
                            {typeof memory.timestamp === 'number'
                              ? new Date(memory.timestamp).toLocaleString()
                              : new Date(memory.timestamp).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                      {memory.content}
                    </p>
                  </div>
                  {(activeType === 'short' || activeType === 'long') && (
                    <button
                      onClick={() => deleteMemory(memory.id)}
                      className="p-1.5 hover:bg-red-50 rounded-lg transition-colors text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
