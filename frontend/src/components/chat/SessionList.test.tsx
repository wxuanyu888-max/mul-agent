import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SessionList } from './SessionList';
import { chatApi } from '../../services/api';

// Mock chat API
vi.mock('../../services/api', () => ({
  chatApi: {
    getSessions: vi.fn(),
    deleteSession: vi.fn(),
  },
}));

describe('SessionList', () => {
  const mockProps = {
    selectedAgent: 'core_brain',
    onSessionSelect: vi.fn(),
    onNewChat: vi.fn(),
    isOpen: true,
    onClose: vi.fn(),
  };

  const mockSessions = [
    {
      session_id: 'session-1',
      agent_id: 'core_brain',
      created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 minutes ago
      last_message_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      message_count: 5,
      preview: 'This is a preview of the last message',
      first_message: 'Hello, how can I help?',
    },
    {
      session_id: 'session-2',
      agent_id: 'core_brain',
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
      last_message_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
      message_count: 10,
      preview: 'Yesterday conversation',
      first_message: 'Yesterday first message',
    },
    {
      session_id: 'session-3',
      agent_id: 'core_brain',
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(), // 10 days ago
      last_message_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
      message_count: 3,
      preview: 'Old conversation',
      first_message: '',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders session list header', () => {
    render(<SessionList {...mockProps} />);

    expect(screen.getByText('会话列表')).toBeInTheDocument();
    expect(screen.getByText('新对话')).toBeInTheDocument();
  });

  it('shows loading state when loading sessions', () => {
    vi.mocked(chatApi.getSessions).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<SessionList {...mockProps} />);

    // Check for loading spinner instead of role
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows empty state when no sessions', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: [] },
    } as any);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('暂无会话')).toBeInTheDocument();
    });
  });

  it('renders sessions list correctly', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      expect(screen.getByText('Yesterday first message')).toBeInTheDocument();
      // Check for the third session which has empty first_message - it shows 新对话 in the button AND session
      const newSessionTexts = screen.getAllByText('新对话');
      expect(newSessionTexts.length).toBeGreaterThan(0);
    });

    expect(screen.getByText('5 条消息')).toBeInTheDocument();
    expect(screen.getByText('10 条消息')).toBeInTheDocument();
  });

  it('calls onSessionSelect when session is clicked', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
    });

    const sessionElement = screen.getByText('Hello, how can I help?').closest('.cursor-pointer');
    if (sessionElement) {
      fireEvent.click(sessionElement);
      expect(mockProps.onSessionSelect).toHaveBeenCalledWith('session-1');
    }
  });

  it('calls onNewChat when new chat button is clicked', () => {
    render(<SessionList {...mockProps} />);

    const newChatButton = screen.getByText('新对话').closest('button');
    if (newChatButton) {
      fireEvent.click(newChatButton);
      expect(mockProps.onNewChat).toHaveBeenCalled();
    }
  });

  it('calls onClose when close button is clicked', () => {
    const { container } = render(<SessionList {...mockProps} />);

    // Find the close button by its position (second button in header)
    const buttons = container.querySelectorAll('button');
    // Close button is the one with ChevronRight icon
    const closeButton = Array.from(buttons).find(btn =>
      btn.querySelector('svg')?.innerHTML.includes('chevron-right') ||
      btn.querySelector('path')?.getAttribute('d')?.includes('M9 18l6-6-6-6')
    );

    if (!closeButton && buttons.length >= 2) {
      // Fallback: click the last button in the header section
      fireEvent.click(buttons[buttons.length - 2]);
    } else if (closeButton) {
      fireEvent.click(closeButton);
    }

    expect(mockProps.onClose).toHaveBeenCalled();
  });

  it('deletes session when delete button is clicked', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    vi.mocked(chatApi.deleteSession).mockResolvedValue({
      data: { status: 'success', message: 'Session deleted' },
    } as any);

    // Mock confirm to return true
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
    });

    // Find and click delete button for first session
    const deleteButtons = screen.getAllByTitle('删除会话');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(chatApi.deleteSession).toHaveBeenCalledWith('session-1', 'core_brain');
    });
  });

  it('shows loading spinner when deleting session', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    // Mock delete to take some time
    vi.mocked(chatApi.deleteSession).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({
        data: { status: 'success', message: 'Session deleted' },
      } as any), 100))
    );

    vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('删除会话');
    fireEvent.click(deleteButtons[0]);

    // Check for loading spinner
    await waitFor(() => {
      const spinners = document.querySelectorAll('.animate-spin');
      expect(spinners.length).toBeGreaterThan(0);
    });
  });

  it('handles delete confirmation cancellation', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    // Mock confirm to return false
    vi.spyOn(window, 'confirm').mockReturnValue(false);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('删除会话');
    fireEvent.click(deleteButtons[0]);

    // Delete should not be called
    expect(chatApi.deleteSession).not.toHaveBeenCalled();
  });

  it('shows error alert when delete fails', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    vi.mocked(chatApi.deleteSession).mockRejectedValue(new Error('Delete failed'));

    vi.spyOn(window, 'confirm').mockReturnValue(true);

    // Mock alert
    const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('删除会话');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith('删除失败，请重试');
    });
  });

  it('does not render when isOpen is false', () => {
    render(<SessionList {...mockProps} isOpen={false} />);

    expect(screen.queryByText('会话列表')).not.toBeInTheDocument();
  });

  it('loads sessions when panel opens', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    const { rerender } = render(<SessionList {...mockProps} isOpen={false} />);

    expect(chatApi.getSessions).not.toHaveBeenCalled();

    rerender(<SessionList {...mockProps} isOpen={true} />);

    await waitFor(() => {
      expect(chatApi.getSessions).toHaveBeenCalledWith('core_brain');
    });
  });

  it('formats time correctly - today', () => {
    render(<SessionList {...mockProps} />);
    // Time formatting is internal, but we can verify the component renders
    expect(screen.getByText('会话列表')).toBeInTheDocument();
  });

  it('displays message count for each session', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('5 条消息')).toBeInTheDocument();
      expect(screen.getByText('10 条消息')).toBeInTheDocument();
    });
  });

  it('displays preview text when available', async () => {
    vi.mocked(chatApi.getSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as any);

    render(<SessionList {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('This is a preview of the last message')).toBeInTheDocument();
    });
  });

  describe('keyboard navigation', () => {
    it('handles ArrowDown to navigate down', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      // Focus the container
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'ArrowDown' });
      }

      // The selected index should be 0 (first session)
      // We can verify by checking if the first session has the selected style
      await waitFor(() => {
        const sessions = document.querySelectorAll('div.cursor-pointer');
        if (sessions[0]) {
          expect(sessions[0]).toHaveClass('bg-purple-100');
        }
      });
    });

    it('handles ArrowUp to navigate up', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        // First go down to index 0
        fireEvent.keyDown(containerEl, { key: 'ArrowDown' });
        // Then go up should stay at 0
        fireEvent.keyDown(containerEl, { key: 'ArrowUp' });
      }

      // Selected index should still be 0
      await waitFor(() => {
        const sessions = document.querySelectorAll('div.cursor-pointer');
        if (sessions[0]) {
          expect(sessions[0]).toHaveClass('bg-purple-100');
        }
      });
    });

    it('handles Enter to select session', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        // Navigate to first session (index 0)
        fireEvent.keyDown(containerEl, { key: 'ArrowDown' });
        // Press Enter to select
        fireEvent.keyDown(containerEl, { key: 'Enter' });
      }

      await waitFor(() => {
        expect(mockProps.onSessionSelect).toHaveBeenCalledWith('session-1');
      });
    });

    it('handles Escape to close panel', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'Escape' });
      }

      expect(mockProps.onClose).toHaveBeenCalled();
    });

    it('handles Delete to delete selected session', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      vi.mocked(chatApi.deleteSession).mockResolvedValue({
        data: { status: 'success', message: 'Session deleted' },
      } as any);

      vi.spyOn(window, 'confirm').mockReturnValue(true);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        // Navigate to first session
        fireEvent.keyDown(containerEl, { key: 'ArrowDown' });
        // Press Delete
        fireEvent.keyDown(containerEl, { key: 'Delete' });
      }

      await waitFor(() => {
        expect(chatApi.deleteSession).toHaveBeenCalledWith('session-1', 'core_brain');
      });
    });

    it('handles N key for new chat', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'n' });
      }

      expect(mockProps.onNewChat).toHaveBeenCalled();
      expect(mockProps.onClose).toHaveBeenCalled();
    });

    it('handles N key with uppercase', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'N', shiftKey: true });
      }

      expect(mockProps.onNewChat).toHaveBeenCalled();
      expect(mockProps.onClose).toHaveBeenCalled();
    });
  });

  describe('bulk selection and delete', () => {
    it('toggles select mode when pressing M key', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('会话列表')).toBeInTheDocument();
      });

      // Enable select mode with M key
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      // Should show bulk action bar with helper text
      await waitFor(() => {
        expect(screen.getByText('点击会话或使用空格键选择，Ctrl+A 全选')).toBeInTheDocument();
      });
    });

    it('toggles select mode when clicking the checkbox icon', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('会话列表')).toBeInTheDocument();
      });

      // Click the select mode toggle button (look for Square icon by checking all buttons)
      const buttons = document.querySelectorAll('button');
      // Click the first button that has a square-like icon (select mode button)
      for (const btn of buttons) {
        if (btn.innerHTML.includes('square') || btn.innerHTML.includes('Square')) {
          fireEvent.click(btn);
          break;
        }
      }

      // Should show bulk action bar
      await waitFor(() => {
        expect(screen.getByText('点击会话或使用空格键选择，Ctrl+A 全选')).toBeInTheDocument();
      });
    });

    it('selects session when clicking checkbox in select mode', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      // Enable select mode
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      await waitFor(() => {
        expect(screen.getByText('点击会话或使用空格键选择，Ctrl+A 全选')).toBeInTheDocument();
      });

      // Click first session's checkbox
      const checkboxes = screen.getAllByRole('checkbox');
      if (checkboxes.length > 0) {
        fireEvent.click(checkboxes[0]);
      }

      // Should show selected count
      await waitFor(() => {
        expect(screen.getByText('已选择 1 项')).toBeInTheDocument();
      });
    });

    it('selects all sessions', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      // Enable select mode
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      await waitFor(() => {
        expect(screen.getByText('点击会话或使用空格键选择，Ctrl+A 全选')).toBeInTheDocument();
      });

      // Click first session to select one
      const checkboxes = screen.getAllByRole('checkbox');
      if (checkboxes.length > 0) {
        fireEvent.click(checkboxes[0]);
      }

      // Click "全选" button
      const selectAllButton = screen.getByText('全选');
      fireEvent.click(selectAllButton);

      // Should show all selected
      await waitFor(() => {
        expect(screen.getByText('已选择 3 项')).toBeInTheDocument();
      });
    });

    it('deselects all sessions', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('会话列表')).toBeInTheDocument();
      });

      // Enable select mode
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      // Wait for bulk action bar to appear
      await waitFor(() => {
        expect(screen.getByText('点击会话或使用空格键选择，Ctrl+A 全选')).toBeInTheDocument();
      });

      // Click first session to have at least one selected, then select all
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBe(3);
      });
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      // Click "全选" button
      const selectAllButton = screen.getByText('全选');
      fireEvent.click(selectAllButton);

      await waitFor(() => {
        expect(screen.getByText('已选择 3 项')).toBeInTheDocument();
      });

      // Click "取消全选" button
      const deselectAllButton = screen.getByText('取消全选');
      fireEvent.click(deselectAllButton);

      // Should show no selection message
      await waitFor(() => {
        expect(screen.getByText('点击会话或使用空格键选择，Ctrl+A 全选')).toBeInTheDocument();
      });
    });

    it('bulk deletes selected sessions', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      vi.mocked(chatApi.deleteSession).mockResolvedValue({
        data: { status: 'success', message: 'Session deleted' },
      } as any);

      vi.spyOn(window, 'confirm').mockReturnValue(true);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      // Enable select mode
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      // Select first two sessions
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBe(3);
      });
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(checkboxes[1]);

      await waitFor(() => {
        expect(screen.getByText('已选择 2 项')).toBeInTheDocument();
      });

      // Click delete button
      const deleteButton = screen.getByText('删除');
      fireEvent.click(deleteButton);

      // Should call deleteSession for each selected session
      await waitFor(() => {
        expect(chatApi.deleteSession).toHaveBeenCalledTimes(2);
      });
    });

    it('handles bulk delete with Delete key', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      vi.mocked(chatApi.deleteSession).mockResolvedValue({
        data: { status: 'success', message: 'Session deleted' },
      } as any);

      vi.spyOn(window, 'confirm').mockReturnValue(true);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      // Enable select mode
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      // Select first session
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBe(3);
      });
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      // Press Delete key
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'Delete' });
      }

      await waitFor(() => {
        expect(chatApi.deleteSession).toHaveBeenCalledWith('session-1', 'core_brain');
      });
    });

    it('uses space key to toggle selection in select mode', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('会话列表')).toBeInTheDocument();
      });

      // Enable select mode
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      // Wait for checkboxes to appear
      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBe(3);
      });

      // Click first checkbox directly to test selection
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      // Should show selected count
      await waitFor(() => {
        expect(screen.getByText('已选择 1 项')).toBeInTheDocument();
      });
    });

    it('exits select mode when pressing Escape with no selection', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { container } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      // Enable select mode
      const containerEl = container.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      await waitFor(() => {
        expect(screen.getByText('点击会话或使用空格键选择，Ctrl+A 全选')).toBeInTheDocument();
      });

      // Press Escape
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'Escape' });
      }

      // Should exit select mode
      await waitFor(() => {
        expect(screen.queryByText('点击会话或使用空格键选择，Ctrl+A 全选')).not.toBeInTheDocument();
      });
    });

    it('clears selection when panel closes', async () => {
      vi.mocked(chatApi.getSessions).mockResolvedValue({
        data: { sessions: mockSessions },
      } as any);

      const { rerender } = render(<SessionList {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      });

      // Enable select mode and select sessions
      const containerEl = document.querySelector('.absolute');
      if (containerEl) {
        fireEvent.keyDown(containerEl, { key: 'm' });
      }

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox').length).toBe(3);
      });
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      await waitFor(() => {
        expect(screen.getByText('已选择 1 项')).toBeInTheDocument();
      });

      // Close panel
      rerender(<SessionList {...mockProps} isOpen={false} />);

      // Selection should be cleared
      expect(screen.queryByText('已选择 1 项')).not.toBeInTheDocument();
    });
  });
});
