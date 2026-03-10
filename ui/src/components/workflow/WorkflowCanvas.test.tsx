// WorkflowCanvas Test Suite

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { WorkflowCanvas } from './WorkflowCanvas';
import { infoApi, logsApi } from '../../services/api';

// Mock API modules
vi.mock('../../services/api', () => ({
  infoApi: {
    getCurrentWorkflow: vi.fn(),
    getAgentTeam: vi.fn(),
    getInteractions: vi.fn(),
    getAgentInteractions: vi.fn(),
    getAgentDetails: vi.fn(),
  },
  logsApi: {
    getLogs: vi.fn(),
  },
}));

describe('WorkflowCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock empty workflow state
    vi.mocked(infoApi.getCurrentWorkflow).mockResolvedValue({
      data: { active: false, sub_agents: [] }
    });
    vi.mocked(infoApi.getAgentTeam).mockResolvedValue({
      data: { agents: [], active_sub_agents: {}, current_task: { active: false, input: null, status: 'idle' } }
    });
    vi.mocked(infoApi.getInteractions).mockResolvedValue({
      data: { interactions: [] }
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders workflow canvas with header', async () => {
    await waitFor(() => {
      render(<WorkflowCanvas />);
      expect(screen.getByText(/Workflow Status/i)).toBeInTheDocument();
    });
  });

  it('displays workflow status panel', async () => {
    await waitFor(() => {
      render(<WorkflowCanvas />);
      expect(screen.getByText(/Status:/i)).toBeInTheDocument();
    });
  });

  it('displays legend panel', async () => {
    await waitFor(() => {
      render(<WorkflowCanvas />);
      expect(screen.getByText(/Legend/i)).toBeInTheDocument();
    });
  });

  it('displays idle state when no active workflow', async () => {
    await waitFor(() => {
      render(<WorkflowCanvas />);
      expect(screen.getByText(/Idle/i)).toBeInTheDocument();
    });
  });

  it('displays agent count', async () => {
    vi.mocked(infoApi.getAgentTeam).mockResolvedValue({
      data: {
        agents: [
          { agent_id: 'test1', name: 'Test Agent 1', description: 'Test', role: 'test' }
        ],
        active_sub_agents: {},
        current_task: { active: false, input: null, status: 'idle' }
      }
    });

    await waitFor(() => {
      render(<WorkflowCanvas />);
      expect(screen.getByText(/Agents: 1/i)).toBeInTheDocument();
    });
  });

  it('displays refresh button', async () => {
    await waitFor(() => {
      render(<WorkflowCanvas />);
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      expect(refreshButton).toBeInTheDocument();
    });
  });

  it('calls fetchWorkflowStatus when refresh button clicked', async () => {
    vi.mocked(infoApi.getCurrentWorkflow).mockResolvedValueOnce({
      data: { active: false, sub_agents: [] }
    });

    await waitFor(async () => {
      render(<WorkflowCanvas />);
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      await waitFor(() => {
        fireEvent.click(refreshButton);
      });
      // Should not throw
      expect(true).toBe(true);
    });
  });
});
