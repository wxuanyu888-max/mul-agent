import React, { useState, useEffect } from 'react';
import { integrationsApi } from '../../services/api';
import type { Integration, IntegrationFormData } from '../../types';
import {
  Plus,
  Pencil,
  Copy,
  Trash2,
  GripVertical,
  CheckCircle,
  Circle,
  Key,
} from 'lucide-react';

interface GlobalConfig {
  url: string;
  provider: string;
  model: string;
  has_key: boolean;
}

const IntegrationList: React.FC = () => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [globalConfig, setGlobalConfig] = useState<GlobalConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'add' | 'edit' | 'global'>('add');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<IntegrationFormData & { key?: string }>({
    name: '',
    url: '',
    provider: '',
    model: '',
    key: '',
    icon: '',
  });
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const loadIntegrations = async () => {
    try {
      const response = await integrationsApi.list();
      if (response.data) {
        setIntegrations(response.data.integrations || []);
      }
    } catch (err) {
      console.error('Failed to load integrations:', err);
    }
  };

  const loadGlobalConfig = async () => {
    try {
      const response = await fetch('/api/llm-config');
      if (response.ok) {
        const data = await response.json();
        setGlobalConfig(data);
      }
    } catch (err) {
      console.error('Failed to load global config:', err);
    }
  };

  useEffect(() => {
    Promise.all([loadIntegrations(), loadGlobalConfig()]).finally(() => {
      setLoading(false);
    });
  }, []);

  const handleAdd = () => {
    setFormData({ name: '', url: '', provider: '', model: '', key: '', icon: '' });
    setModalMode('add');
    setShowModal(true);
  };

  const handleEdit = (integration: Integration) => {
    setFormData({
      name: integration.name,
      url: integration.url,
      provider: integration.provider,
      model: integration.model || '',
      key: '',
      icon: integration.icon || '',
    });
    setEditingId(integration.id);
    setModalMode('edit');
    setShowModal(true);
  };

  const handleEditGlobal = () => {
    setFormData({
      name: 'Global LLM Configuration',
      url: globalConfig?.url || '',
      provider: globalConfig?.provider || '',
      model: globalConfig?.model || '',
      key: '',
      icon: '',
    });
    setModalMode('global');
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formData.url || !formData.provider) {
      setError('Please fill in required fields (URL, provider)');
      return;
    }

    if (modalMode === 'add' && !formData.key) {
      setError('Please provide an API key');
      return;
    }

    if (modalMode === 'global' && !formData.key && !globalConfig?.has_key) {
      setError('Please provide an API key');
      return;
    }

    setActionLoading('save');
    setError(null);

    try {
      if (modalMode === 'add') {
        await integrationsApi.create(formData);
        await loadIntegrations();
      } else if (modalMode === 'edit' && editingId) {
        await integrationsApi.update(editingId, formData);
        await loadIntegrations();
      } else if (modalMode === 'global') {
        const saveData = {
          url: formData.url,
          provider: formData.provider,
          model: formData.model || 'default',
          key: formData.key || '',
        };
        const response = await fetch('/api/llm-config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(saveData),
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || 'Failed to save');
        }
        await loadGlobalConfig();
      }
      setShowModal(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this integration?')) return;
    setActionLoading(`delete-${id}`);
    try {
      await integrationsApi.delete(id);
      await loadIntegrations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDuplicate = async (id: string) => {
    setActionLoading(`duplicate-${id}`);
    try {
      await integrationsApi.duplicate(id);
      await loadIntegrations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate');
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleStatus = async (integration: Integration) => {
    setActionLoading(`toggle-${integration.id}`);
    try {
      await integrationsApi.update(integration.id, {
        status: integration.status === 'active' ? 'inactive' : 'active',
      });
      await loadIntegrations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteGlobal = async () => {
    if (!confirm('Delete global LLM configuration?')) return;
    setActionLoading('delete-global');
    try {
      const response = await fetch('/api/llm-config', { method: 'DELETE' });
      if (response.ok) setGlobalConfig(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    const newIntegrations = [...integrations];
    const draggedItem = newIntegrations[draggedIndex];
    newIntegrations.splice(draggedIndex, 1);
    newIntegrations.splice(index, 0, draggedItem);
    setIntegrations(newIntegrations);
    setDraggedIndex(index);
  };

  const handleDragEnd = async () => {
    if (draggedIndex !== null) {
      const reorderData = integrations.map((item, index) => ({ id: item.id, order: index }));
      try {
        await integrationsApi.reorder(reorderData);
      } catch (err) {
        console.error('Failed to reorder:', err);
      }
    }
    setDraggedIndex(null);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-gray-900">Settings</h1>
        <button
          onClick={handleAdd}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-sm rounded hover:bg-gray-800"
        >
          <Plus className="w-4 h-4" />
          Add
        </button>
      </div>

      {error && (
        <div className="mb-4 p-2.5 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {/* Global LLM Configuration Card */}
        <div className="bg-white border rounded p-4">
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center">
                <Key className="w-4 h-4 text-gray-700" />
              </div>
              <div>
                <h2 className="font-medium text-gray-900 text-sm">Global LLM Configuration</h2>
                <p className="text-xs text-gray-500">Shared across all agents</p>
              </div>
            </div>
            {globalConfig?.has_key && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                <CheckCircle className="w-3 h-3" />
                Configured
              </span>
            )}
          </div>

          {globalConfig?.provider ? (
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div>
                <p className="text-xs text-gray-500">Provider</p>
                <p className="text-sm font-medium">{globalConfig.provider}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Model</p>
                <p className="text-sm font-medium">{globalConfig.model}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">API URL</p>
                <p className="text-xs text-gray-700 truncate">{globalConfig.url}</p>
              </div>
            </div>
          ) : (
            <p className="text-xs text-gray-500 mb-3">No LLM configuration set</p>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleEditGlobal}
              disabled={actionLoading === 'save'}
              className="flex items-center gap-1 px-2.5 py-1 bg-gray-900 text-white text-xs rounded hover:bg-gray-800 disabled:opacity-50"
            >
              <Pencil className="w-3 h-3" />
              {globalConfig?.has_key ? 'Edit' : 'Configure'}
            </button>
            {globalConfig?.has_key && (
              <button
                onClick={handleDeleteGlobal}
                disabled={actionLoading === 'delete-global'}
                className="flex items-center gap-1 px-2.5 py-1 text-red-600 text-xs rounded hover:bg-red-50 disabled:opacity-50"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            )}
          </div>
        </div>

        {/* Integration Cards */}
        <div className="pt-3 border-t">
          <h3 className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">
            Platform Integrations
          </h3>

          {integrations.length === 0 ? (
            <div className="text-center py-6 border border-dashed rounded">
              <p className="text-sm text-gray-500">No integrations configured</p>
            </div>
          ) : (
            <div className="space-y-2">
              {integrations.map((integration, index) => (
                <div
                  key={integration.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDragEnd={handleDragEnd}
                  className={`bg-white border rounded p-3 hover:shadow-sm transition-all cursor-move ${
                    draggedIndex === index ? 'opacity-50 bg-gray-50' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="text-gray-400 cursor-grab active:cursor-grabbing">
                      <GripVertical className="w-4 h-4" />
                    </div>

                    <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center flex-shrink-0">
                      {integration.icon ? (
                        <img src={integration.icon} alt={integration.name} className="w-5 h-5" />
                      ) : (
                        <Key className="w-4 h-4 text-gray-600" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900 text-sm">{integration.name}</h3>
                        {integration.status === 'active' && (
                          <span className="flex items-center gap-1 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                            <CheckCircle className="w-2.5 h-2.5" />
                            Active
                          </span>
                        )}
                      </div>
                      <a
                        href={integration.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-gray-600 hover:underline truncate block"
                      >
                        {integration.url}
                      </a>
                    </div>

                    <div className="flex items-center gap-0.5">
                      <button
                        onClick={() => handleToggleStatus(integration)}
                        disabled={actionLoading?.startsWith(`toggle-${integration.id}`)}
                        className={`p-1.5 rounded transition-colors ${
                          integration.status === 'active'
                            ? 'text-green-600 hover:bg-green-50'
                            : 'text-gray-400 hover:bg-gray-100'
                        }`}
                        title={integration.status === 'active' ? 'Deactivate' : 'Activate'}
                      >
                        {integration.status === 'active' ? (
                          <CheckCircle className="w-4 h-4" />
                        ) : (
                          <Circle className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleEdit(integration)}
                        disabled={actionLoading !== null}
                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                        title="Edit"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDuplicate(integration.id)}
                        disabled={actionLoading?.startsWith(`duplicate-${integration.id}`)}
                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                        title="Duplicate"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(integration.id)}
                        disabled={actionLoading?.startsWith(`delete-${integration.id}`)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded p-5 w-full max-w-sm shadow-lg">
            <h2 className="text-base font-semibold mb-4">
              {modalMode === 'add' ? 'Add Integration' : modalMode === 'edit' ? 'Edit Integration' : 'Edit Global Configuration'}
            </h2>

            <div className="space-y-3">
              {modalMode !== 'global' && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
                    placeholder="e.g., OpenAI, Anthropic"
                    autoFocus={modalMode === 'add'}
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Provider *</label>
                <input
                  type="text"
                  value={formData.provider}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
                  placeholder="e.g., openai, anthropic"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">API URL *</label>
                <input
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
                  placeholder="https://api.example.com/v1"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Model</label>
                <input
                  type="text"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
                  placeholder="e.g., gpt-4, claude-3"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  API Key {modalMode === 'global' && !globalConfig?.has_key ? '*' : ''}
                </label>
                <input
                  type="password"
                  value={formData.key}
                  onChange={(e) => setFormData({ ...formData, key: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
                  placeholder={modalMode === 'global' ? 'Enter new key to update' : 'sk-...'}
                />
                {modalMode === 'global' && globalConfig?.has_key && (
                  <p className="mt-1 text-xs text-gray-500">Leave empty to keep existing key</p>
                )}
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <button
                onClick={handleSave}
                disabled={actionLoading === 'save'}
                className="flex-1 px-3 py-1.5 bg-gray-900 text-white text-sm rounded hover:bg-gray-800 disabled:opacity-50"
              >
                {actionLoading === 'save' ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={() => setShowModal(false)}
                disabled={actionLoading !== null}
                className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IntegrationList;
