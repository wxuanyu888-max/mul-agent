import { useState, useEffect } from 'react';
import { Folder, Plus, Trash2, ChevronDown, Check } from 'lucide-react';
import { projectsApi } from '../../services/api';
import type { Project } from '../../types';

interface ProjectSwitcherProps {
  selectedProjectId?: string;
  onProjectChange: (projectId: string | null) => void;
}

export function ProjectSwitcher({ selectedProjectId, onProjectChange }: ProjectSwitcherProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load projects
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const res = await projectsApi.list();
      setProjects(res.data.projects || []);
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const handleCreateProject = async (name: string, description: string) => {
    setLoading(true);
    try {
      await projectsApi.create(name, description);
      await loadProjects();
      setShowCreateModal(false);
    } catch (error) {
      console.error('Failed to create project:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProject = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    if (!confirm(`Are you sure you want to delete project "${projectId}"? This will delete all agents in this project.`)) {
      return;
    }

    setLoading(true);
    try {
      await projectsApi.delete(projectId);
      await loadProjects();
      if (selectedProjectId === projectId) {
        onProjectChange(null);
      }
    } catch (error) {
      console.error('Failed to delete project:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectedProject = projects.find(p => p.project_id === selectedProjectId);

  return (
    <div className="relative">
      {/* Project Selector Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
      >
        <Folder className="w-4 h-4 text-purple-500" />
        <span className="text-sm font-medium text-gray-700">
          {selectedProject?.name || 'All Projects'}
        </span>
        {projects.length > 0 && (
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-xl border border-gray-200 shadow-xl z-20 overflow-hidden">
            {/* Header */}
            <div className="px-3 py-2 border-b border-gray-100 bg-gray-50">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Projects
              </span>
            </div>

            {/* Project List */}
            <div className="max-h-64 overflow-y-auto">
              {/* Global option */}
              <button
                onClick={() => {
                  onProjectChange(null);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-50 transition-colors ${
                  !selectedProjectId ? 'bg-purple-50' : ''
                }`}
              >
                <div className={`w-4 h-4 rounded flex items-center justify-center ${
                  !selectedProjectId ? 'bg-purple-500' : 'border border-gray-300'
                }`}>
                  {!selectedProjectId && <Check className="w-3 h-3 text-white" />}
                </div>
                <div className="flex-1 text-left">
                  <span className="text-sm font-medium text-gray-900">All Projects</span>
                  <p className="text-xs text-gray-500">Show all agents</p>
                </div>
              </button>

              {/* Projects */}
              {projects.map((project) => (
                <div
                  key={project.project_id}
                  className="group flex items-center"
                >
                  <button
                    onClick={() => {
                      onProjectChange(project.project_id);
                      setIsOpen(false);
                    }}
                    className={`flex-1 flex items-center gap-2 px-3 py-2 hover:bg-gray-50 transition-colors ${
                      selectedProjectId === project.project_id ? 'bg-purple-50' : ''
                    }`}
                  >
                    <div className={`w-4 h-4 rounded flex items-center justify-center ${
                      selectedProjectId === project.project_id ? 'bg-purple-500' : 'border border-gray-300'
                    }`}>
                      {selectedProjectId === project.project_id && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <div className="flex-1 text-left min-w-0">
                      <span className="text-sm font-medium text-gray-900 truncate block">{project.name}</span>
                      <p className="text-xs text-gray-500">{project.agent_count} agents</p>
                    </div>
                  </button>

                  {/* Delete Button */}
                  <button
                    onClick={(e) => handleDeleteProject(e, project.project_id)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 mr-2 hover:bg-red-50 rounded transition-opacity"
                    disabled={loading}
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-500" />
                  </button>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-3 py-2 border-t border-gray-100 bg-gray-50">
              <button
                onClick={() => {
                  setShowCreateModal(true);
                  setIsOpen(false);
                }}
                className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors text-sm font-medium"
              >
                <Plus className="w-4 h-4" />
                New Project
              </button>
            </div>
          </div>
        </>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateProject}
          loading={loading}
        />
      )}
    </div>
  );
}

interface CreateProjectModalProps {
  onClose: () => void;
  onCreate: (name: string, description: string) => void;
  loading: boolean;
}

function CreateProjectModal({ onClose, onCreate, loading }: CreateProjectModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onCreate(name, description);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <form onSubmit={handleSubmit}>
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Create New Project</h2>
            <p className="text-sm text-gray-500 mt-1">Organize your agents into projects</p>
          </div>

          {/* Body */}
          <div className="px-6 py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm"
                placeholder="e.g., My Web App"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm"
                rows={3}
                placeholder="Describe what this project is about..."
              />
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-purple-500 hover:bg-purple-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
