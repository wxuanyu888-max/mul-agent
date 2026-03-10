import { useState, useEffect, useRef, useCallback } from 'react';
import { MessageSquare, Trash2, ChevronRight, Plus, Clock, CheckSquare, Square, X } from 'lucide-react';
import { chatApi } from '../../services/api';

interface Session {
  session_id: string;
  agent_id: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
  preview: string;
  first_message?: string;
}

interface SessionListProps {
  selectedAgent?: string;
  onSessionSelect: (sessionId: string) => void;
  onNewChat: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export function SessionList({
  selectedAgent,
  onSessionSelect,
  onNewChat,
  isOpen,
  onClose,
}: SessionListProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const sessionRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen, selectedAgent]);

  // Reset selected index when sessions change
  useEffect(() => {
    setSelectedIndex(-1);
  }, [sessions]);

  // Reset select mode and selected sessions when panel closes
  useEffect(() => {
    if (!isOpen) {
      setSelectMode(false);
      setSelectedSessions(new Set());
    }
  }, [isOpen]);

  // Scroll selected session into view
  useEffect(() => {
    if (selectedIndex >= 0 && sessionRefs.current[selectedIndex]) {
      const element = sessionRefs.current[selectedIndex];
      if (element && typeof element.scrollIntoView === 'function') {
        element.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
      }
    }
  }, [selectedIndex]);

  // Keyboard navigation handler
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Don't handle when composing with IME
    if (e.nativeEvent.isComposing) {
      return;
    }

    // If in select mode, handle selection shortcuts
    if (selectMode) {
      switch (e.key) {
        case 'Escape':
          if (selectedSessions.size > 0) {
            deselectAll();
          } else {
            setSelectMode(false);
          }
          break;
        case 'a':
        case 'A':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            selectAll();
          }
          break;
        case ' ':
          if (selectedIndex >= 0 && sessions[selectedIndex]) {
            e.preventDefault();
            toggleSessionSelection(sessions[selectedIndex].session_id);
          }
          break;
        case 'Delete':
        case 'Backspace':
          if (selectedSessions.size > 0) {
            e.preventDefault();
            handleBulkDelete();
          }
          break;
      }
      return;
    }

    // Normal navigation
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, sessions.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        if (selectedIndex >= 0 && sessions[selectedIndex]) {
          e.preventDefault();
          onSessionSelect(sessions[selectedIndex].session_id);
        }
        break;
      case 'Delete':
      case 'Backspace':
        if (selectedIndex >= 0 && sessions[selectedIndex]) {
          e.preventDefault();
          const session = sessions[selectedIndex];
          if (!deleting && confirm('确定要删除这个会话吗？此操作不可恢复。')) {
            handleDeleteInternal(session.session_id);
          }
        }
        break;
      case 'Escape':
        onClose();
        break;
      case 'n':
      case 'N':
        // Quick new chat shortcut
        if (!e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          onNewChat();
          onClose();
        }
        break;
      case 'm':
      case 'M':
        // Toggle multi-select mode
        if (!e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          toggleSelectMode();
        }
        break;
    }
  }, [sessions, selectedIndex, onClose, onNewChat, deleting, selectMode, selectedSessions]);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const res = await chatApi.getSessions(selectedAgent);
      setSessions(res.data.sessions || []);
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setSessions([]); // Set empty array on error to avoid undefined state
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    await handleDeleteInternal(sessionId);
  };

  const handleDeleteInternal = async (sessionId: string) => {
    if (!confirm('确定要删除这个会话吗？此操作不可恢复。')) {
      return;
    }

    setDeleting(sessionId);
    try {
      await chatApi.deleteSession(sessionId, selectedAgent);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      // Remove from selected sessions if present
      setSelectedSessions((prev) => {
        const next = new Set(prev);
        next.delete(sessionId);
        return next;
      });
      // Adjust selected index if needed
      setSelectedIndex((prev) => {
        const deletedIndex = sessions.findIndex((s) => s.session_id === sessionId);
        if (prev === deletedIndex) {
          return Math.max(0, sessions.length - 2);
        }
        return prev > deletedIndex ? prev - 1 : prev;
      });
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('删除失败，请重试');
    } finally {
      setDeleting(null);
    }
  };

  // Toggle select mode
  const toggleSelectMode = () => {
    setSelectMode(!selectMode);
    setSelectedSessions(new Set());
  };

  // Toggle session selection
  const toggleSessionSelection = (sessionId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedSessions((prev) => {
      const next = new Set(prev);
      if (next.has(sessionId)) {
        next.delete(sessionId);
      } else {
        next.add(sessionId);
      }
      return next;
    });
  };

  // Select all sessions
  const selectAll = () => {
    setSelectedSessions(new Set(sessions.map((s) => s.session_id)));
  };

  // Deselect all sessions
  const deselectAll = () => {
    setSelectedSessions(new Set());
  };

  // Bulk delete selected sessions
  const handleBulkDelete = async () => {
    if (selectedSessions.size === 0) return;

    const count = selectedSessions.size;
    if (!confirm(`确定要删除选中的 ${count} 个会话吗？此操作不可恢复。`)) {
      return;
    }

    setBulkDeleting(true);
    try {
      const deletePromises = Array.from(selectedSessions).map((sessionId) =>
        chatApi.deleteSession(sessionId, selectedAgent)
      );
      await Promise.all(deletePromises);

      setSessions((prev) =>
        prev.filter((s) => !selectedSessions.has(s.session_id))
      );
      setSelectedSessions(new Set());
      setSelectMode(false);
    } catch (err) {
      console.error('Failed to bulk delete sessions:', err);
      alert('批量删除失败，请重试');
    } finally {
      setBulkDeleting(false);
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN');
    }
  };

  if (!isOpen) return null;

  const hasSelected = selectedSessions.size > 0;

  return (
    <div
      className="absolute inset-y-0 left-0 w-80 bg-white border-r border-gray-200 shadow-lg z-20 flex flex-col"
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-purple-100">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-purple-600" />
            会话列表
          </h2>
          <div className="flex items-center gap-2">
            {/* Select Mode Toggle */}
            <button
              onClick={toggleSelectMode}
              className={`p-1.5 rounded-lg transition-colors ${
                selectMode
                  ? 'bg-purple-600 text-white'
                  : 'hover:bg-white/50 text-gray-500'
              }`}
              title="批量管理 (M)"
            >
              {selectMode ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1 hover:bg-white/50 rounded-lg transition-colors text-gray-500"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Bulk Action Bar */}
        {selectMode && (
          <div className="flex items-center gap-2 p-2 bg-white/70 rounded-lg mb-2">
            {hasSelected ? (
              <>
                <span className="text-sm text-purple-600 font-medium">
                  已选择 {selectedSessions.size} 项
                </span>
                <button
                  onClick={selectAll}
                  className="text-xs px-2 py-1 hover:bg-purple-100 rounded text-purple-600"
                >
                  全选
                </button>
                <button
                  onClick={deselectAll}
                  className="text-xs px-2 py-1 hover:bg-purple-100 rounded text-purple-600"
                >
                  取消全选
                </button>
                <button
                  onClick={handleBulkDelete}
                  disabled={bulkDeleting}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded text-sm font-medium"
                >
                  {bulkDeleting ? (
                    <div className="animate-spin rounded-full h-3 w-3 border-2 border-white border-t-transparent" />
                  ) : (
                    <Trash2 className="w-3 h-3" />
                  )}
                  删除
                </button>
                <button
                  onClick={() => {
                    setSelectMode(false);
                    setSelectedSessions(new Set());
                  }}
                  className="p-1 hover:bg-gray-200 rounded text-gray-500"
                >
                  <X className="w-4 h-4" />
                </button>
              </>
            ) : (
              <span className="text-sm text-gray-500">
                点击会话或使用空格键选择，Ctrl+A 全选
              </span>
            )}
          </div>
        )}

        <button
          onClick={() => {
            onNewChat();
            onClose();
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium text-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          新对话
        </button>
      </div>

      {/* Sessions List */}
      <div ref={listRef} className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-purple-600 border-t-transparent" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <MessageSquare className="w-12 h-12 mb-3 opacity-20" />
            <p className="text-sm">暂无会话</p>
            <p className="text-xs mt-1">开始一个新的对话吧</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {sessions.map((session, index) => {
              const isSelected = selectedSessions.has(session.session_id);
              return (
                <div
                  key={session.session_id}
                  ref={(el) => {
                    sessionRefs.current[index] = el;
                  }}
                  onClick={() => {
                    if (selectMode) {
                      toggleSessionSelection(session.session_id);
                    } else {
                      onSessionSelect(session.session_id);
                    }
                  }}
                  className={`p-4 transition-colors hover:bg-purple-50 ${
                    deleting === session.session_id ? 'opacity-50' : ''
                  } ${
                    selectedIndex === index ? 'bg-purple-100 border-l-4 border-purple-600' : ''
                  } ${
                    isSelected ? 'bg-purple-50 border-l-4 border-purple-600' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Checkbox for select mode */}
                    {selectMode && (
                      <div className="flex-shrink-0 pt-1">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSessionSelection(session.session_id)}
                          onClick={(e) => e.stopPropagation()}
                          className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                        />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 font-medium truncate">
                        {session.first_message || '新对话'}
                      </p>
                      {session.preview && (
                        <p className="text-xs text-gray-500 truncate mt-1">
                          {session.preview}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-2">
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span className="text-xs text-gray-400">
                          {formatTime(session.last_message_at)}
                        </span>
                        <span className="text-xs text-gray-400">•</span>
                        <span className="text-xs text-gray-400">
                          {session.message_count} 条消息
                        </span>
                      </div>
                    </div>
                    {!selectMode && (
                      <button
                        onClick={(e) => handleDelete(e, session.session_id)}
                        disabled={deleting === session.session_id}
                        className="p-1.5 hover:bg-red-50 rounded-lg transition-colors text-gray-400 hover:text-red-600 flex-shrink-0"
                        title="删除会话"
                      >
                        {deleting === session.session_id ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-red-600 border-t-transparent" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
