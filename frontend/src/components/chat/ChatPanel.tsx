import { useState, useEffect, useRef } from 'react';
import { Send, User, Bot, Loader2, RefreshCw, Trash2, Menu, MessageSquare } from 'lucide-react';
import { chatApi, infoApi } from '../../services/api';
import { AgentStatePanel } from './AgentStatePanel';
import { CommandAutocomplete, CommandSuggestion } from './CommandAutocomplete';
import { SessionList } from './SessionList';
import { Message, Agent } from '../../types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Available commands (should match backend commands)
const AVAILABLE_COMMANDS: CommandSuggestion[] = [
  {
    command_id: 'help',
    command_name: 'help',
    command_description: 'Show help information',
    command_aliases: ['h', '?', '援助'],
  },
  {
    command_id: 'status',
    command_name: 'status',
    command_description: 'Show agent status',
    command_aliases: ['st', '状态'],
  },
  {
    command_id: 'list',
    command_name: 'list',
    command_description: 'List items (skills, hooks, commands, etc.)',
    command_aliases: ['ls', '列表'],
  },
  {
    command_id: 'skill',
    command_name: 'skill',
    command_description: 'Manage skills',
    command_aliases: ['sk', '技能'],
  },
  {
    command_id: 'hook',
    command_name: 'hook',
    command_description: 'Manage hooks',
    command_aliases: ['hk', '钩子'],
  },
  {
    command_id: 'memory',
    command_name: 'memory',
    command_description: 'Manage memory',
    command_aliases: ['mem', '记忆'],
  },
  {
    command_id: 'bash',
    command_name: 'bash',
    command_description: 'Execute shell commands',
    command_aliases: ['$', 'sh', '执行'],
  },
];

// Markdown rendering styles
const markdownComponents = {
  p: ({ node, ...props }: any) => <p className="mb-2 last:mb-0" {...props} />,
  code: ({ node, inline, className, children, ...props }: any) => {
    if (inline) {
      return (
        <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono text-red-600" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  pre: ({ node, ...props }: any) => (
    <pre className="my-2 p-3 bg-gray-100 rounded-lg overflow-x-auto text-sm font-mono" {...props} />
  ),
  ul: ({ node, ...props }: any) => <ul className="list-disc list-inside mb-2 space-y-1" {...props} />,
  ol: ({ node, ...props }: any) => <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />,
  li: ({ node, ...props }: any) => <li className="ml-2" {...props} />,
  h1: ({ node, ...props }: any) => <h1 className="text-lg font-bold mt-3 mb-2" {...props} />,
  h2: ({ node, ...props }: any) => <h2 className="text-base font-bold mt-3 mb-2" {...props} />,
  h3: ({ node, ...props }: any) => <h3 className="text-sm font-bold mt-2 mb-1" {...props} />,
  blockquote: ({ node, ...props }: any) => (
    <blockquote className="border-l-4 border-gray-300 pl-4 italic my-2" {...props} />
  ),
  table: ({ node, ...props }: any) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full border border-gray-200" {...props} />
    </div>
  ),
  th: ({ node, ...props }: any) => (
    <th className="border border-gray-200 px-3 py-2 bg-gray-50 font-semibold" {...props} />
  ),
  td: ({ node, ...props }: any) => (
    <td className="border border-gray-200 px-3 py-2" {...props} />
  ),
};

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [showSessionList, setShowSessionList] = useState(false);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [hasSuggestions, setHasSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load agents and sessions
  useEffect(() => {
    const loadData = async () => {
      // Load agents
      try {
        const res = await infoApi.getAgentTeam();
        const agentsList = res.data.agents || [];
        setAgents(agentsList);
        if (agentsList.length > 0 && !selectedAgent) {
          setSelectedAgent(agentsList[0].agent_id);
        }
      } catch (err) {
        console.error('Failed to load agents:', err);
      }

      // Load recent sessions
      await loadSessions();
    };

    loadData();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await chatApi.getSessions(selectedAgent);
      const sessions = res.data.sessions || [];
      if (sessions.length > 0 && !currentSessionId) {
        // Load most recent session
        loadSessionMessages(sessions[0].session_id);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  };

  const loadSessionMessages = async (sessionId: string) => {
    try {
      const res = await chatApi.getSessionMessages(sessionId, selectedAgent);
      const messages = res.data.messages || [];
      setMessages(
        messages.map((msg) => ({
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content,
          // Use timestamp from backend if available, otherwise use current time
          timestamp: msg.timestamp ? new Date(msg.timestamp).getTime() : Date.now(),
        }))
      );
      setCurrentSessionId(sessionId);
    } catch (err) {
      console.error('Failed to load session messages:', err);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentSessionId('');
    setInput('');
  };

  const handleSessionSelect = (sessionId: string) => {
    loadSessionMessages(sessionId);
    setShowSessionList(false);
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatApi.sendMessage({
        message: userMessage.content,
        agent_id: selectedAgent || undefined,
        conversation_id: currentSessionId || undefined,
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Update session ID if this is a new conversation
      if (response.data.conversation_id && !currentSessionId) {
        setCurrentSessionId(response.data.conversation_id);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Error: Failed to get response from agent',
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleCommandSelect = (commandName: string) => {
    // Replace the command prefix with the selected command
    const prefixMatch = input.match(/^[/！？.]\S*/);
    if (prefixMatch) {
      const newValue = '/' + commandName + ' ';
      setInput(newValue);
    } else {
      setInput('/' + commandName + ' ');
    }
    setShowAutocomplete(false);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    // Don't handle when composing with IME (Chinese, Japanese, Korean, etc.)
    if (e.nativeEvent.isComposing) {
      return;
    }

    // Handle keyboard navigation for autocomplete
    if (showAutocomplete && hasSuggestions) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
        setSelectedIndex((prev) => Math.min(prev + 1, AVAILABLE_COMMANDS.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        e.stopPropagation();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        return;
      }
      if (e.key === 'Tab') {
        e.preventDefault();
        e.stopPropagation();
        // Get the filtered suggestions
        const cmdInput = input.replace(/^[/！？.]/, '').toLowerCase();
        const filtered = AVAILABLE_COMMANDS.filter((cmd) =>
          cmd.command_name.toLowerCase().startsWith(cmdInput)
        );
        const selected = filtered[selectedIndex] || filtered[0];
        if (selected) {
          handleCommandSelect(selected.command_name);
        }
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        setShowAutocomplete(false);
        return;
      }
      // Enter selects the current suggestion
      if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        // Get the filtered suggestions
        const cmdInput = input.replace(/^[/！？.]/, '').toLowerCase();
        const filtered = AVAILABLE_COMMANDS.filter((cmd) =>
          cmd.command_name.toLowerCase().startsWith(cmdInput)
        );
        const selected = filtered[selectedIndex] || filtered[0];
        if (selected) {
          handleCommandSelect(selected.command_name);
        }
        return;
      }
    }

    // Normal submit
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Check if we should show autocomplete
  useEffect(() => {
    // Show autocomplete when input starts with /, !, ?, or .
    const shouldShow = /^[/！？.]\S*$/.test(input) || /^[/！？.]$/.test(input);
    setShowAutocomplete(shouldShow);
    // Reset selected index when input changes
    if (shouldShow) {
      setSelectedIndex(0);
    }
  }, [input]);

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-full bg-white relative">
      {/* Session List Sidebar */}
      <SessionList
        isOpen={showSessionList}
        onClose={() => setShowSessionList(false)}
        onSessionSelect={handleSessionSelect}
        onNewChat={handleNewChat}
        selectedAgent={selectedAgent}
      />

      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Session List Toggle */}
            <button
              onClick={() => setShowSessionList(!showSessionList)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
              title="会话列表"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-100 to-purple-200 flex items-center justify-center">
              <Bot className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
              <p className="text-sm text-gray-500">
                {currentSessionId ? '会话中' : `${agents.length} 个 Agent`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* New Chat Button */}
            <button
              onClick={handleNewChat}
              className="p-2 hover:bg-purple-50 rounded-lg transition-colors text-purple-600"
              title="新对话"
            >
              <MessageSquare className="w-5 h-5" />
            </button>

            {/* Agent Selector */}
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">All Agents</option>
              {agents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id}>
                  {agent.name}
                </option>
              ))}
            </select>

            {/* Clear Button */}
            <button
              onClick={clearChat}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
              title="Clear chat"
            >
              <Trash2 className="w-5 h-5" />
            </button>

            {/* Refresh Button */}
            <button
              onClick={() => window.location.reload()}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
              title="Refresh"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 bg-gray-50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Bot className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-medium">No messages yet</p>
            <p className="text-sm mt-1">Start a conversation with your agent team</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={index}
                  className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
                >
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isUser
                        ? 'bg-gradient-to-br from-blue-100 to-blue-200'
                        : 'bg-gradient-to-br from-purple-100 to-purple-200'
                    }`}
                  >
                    {isUser ? (
                      <User className="w-4 h-4 text-blue-600" />
                    ) : (
                      <Bot className="w-4 h-4 text-purple-600" />
                    )}
                  </div>
                  <div
                    className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                      isUser
                        ? 'bg-blue-500 text-white rounded-br-none'
                        : 'bg-white border border-gray-200 text-gray-900 rounded-bl-none shadow-sm'
                    }`}
                  >
                    {isUser ? (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="text-sm">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                    <p
                      className={`text-xs mt-1 ${
                        isUser ? 'text-blue-100' : 'text-gray-400'
                      }`}
                    >
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              );
            })}
            {loading && (
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-100 to-purple-200 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-purple-600" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-purple-600 animate-spin" />
                    <span className="text-sm text-gray-500">Agent is thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Agent State Panel */}
      {selectedAgent && <AgentStatePanel agentId={selectedAgent} />}

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-200 bg-white">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Type your message... (try /help, /status, /list)"
              rows={1}
              className="w-full resize-none bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-gray-700 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent max-h-32"
              style={{ minHeight: '44px' }}
            />
            {showAutocomplete && (
              <CommandAutocomplete
                input={input}
                onSelect={handleCommandSelect}
                onClose={() => setShowAutocomplete(false)}
                hasSuggestions={hasSuggestions}
                setHasSuggestions={setHasSuggestions}
                selectedIndex={selectedIndex}
              />
            )}
          </div>
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 disabled:from-gray-300 disabled:to-gray-400 text-white rounded-xl font-medium text-sm transition-all disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
