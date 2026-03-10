// MemoryPanel Test Suite

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryPanel } from './MemoryPanel';
import { memoryApi } from '../../services/api';

// Mock API modules
vi.mock('../../services/api', () => ({
  memoryApi: {
    getShortTerm: vi.fn(),
    getLongTerm: vi.fn(),
    getHandover: vi.fn(),
    write: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('MemoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock all memory endpoints to return empty arrays
    vi.mocked(memoryApi.getShortTerm).mockResolvedValue({ data: { memories: [], total: 0 } } as any);
    vi.mocked(memoryApi.getLongTerm).mockResolvedValue({ data: { memories: [], total: 0 } } as any);
    vi.mocked(memoryApi.getHandover).mockResolvedValue({ data: { memories: [] } } as any);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders memory panel with header', async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });

    // Use getAllBy since there are multiple "Memory" texts (header + button)
    const memoryHeaders = screen.getAllByText(/Memory/i);
    expect(memoryHeaders.length).toBeGreaterThan(0);
  });

  it('displays empty state when no memories', async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });

    await waitFor(() => {
      expect(screen.getByText(/暂无记忆/i)).toBeInTheDocument();
    });
  });

  it('displays memory tabs', async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });

    expect(screen.getByText(/短期记忆/i)).toBeInTheDocument();
    expect(screen.getByText(/长期记忆/i)).toBeInTheDocument();
    expect(screen.getByText(/交接记忆/i)).toBeInTheDocument();
  });

  it('switches between memory types', async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });

    // Click long-term tab
    const longTermTab = screen.getByText(/长期记忆/i);
    await act(async () => {
      fireEvent.click(longTermTab);
    });

    // Should still show empty state
    await waitFor(() => {
      expect(screen.getByText(/暂无记忆/i)).toBeInTheDocument();
    });
  });

  it('has refresh button', async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    expect(refreshButton).toBeInTheDocument();
  });

  it('displays memories when loaded', async () => {
    const mockMemories = {
      memories: [
        {
          id: '1',
          type: 'short_term',
          timestamp: '2024-01-01T00:00:00',
          content: 'Test memory content'
        }
      ],
      total: 1
    };

    vi.mocked(memoryApi.getShortTerm).mockResolvedValue({ data: mockMemories } as any);
    vi.mocked(memoryApi.getLongTerm).mockResolvedValue({ data: { memories: [], total: 0 } } as any);
    vi.mocked(memoryApi.getHandover).mockResolvedValue({ data: { memories: [] } } as any);

    await act(async () => {
      render(<MemoryPanel />);
    });

    await waitFor(() => {
      expect(screen.getByText(/Test memory content/i)).toBeInTheDocument();
    });
  });

  it('shows loading state', async () => {
    // Make fetch hang to test loading state
    vi.mocked(memoryApi.getShortTerm).mockImplementation(
      () => new Promise(() => {})
    );

    await act(async () => {
      render(<MemoryPanel />);
    });

    // Should show loading indicator
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });
});
