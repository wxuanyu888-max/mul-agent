// Test file

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryPanel } from '../components/memory/MemoryPanel';

// Mock fetch API
global.fetch = vi.fn();

describe('MemoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders memory panel with header', () => {
    render(<MemoryPanel />);

    expect(screen.getByText(/memory/i)).toBeInTheDocument();
  });

  it('displays empty state when no memories', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ memories: [], total: 0 })
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/no memories yet/i)).toBeInTheDocument();
    });
  });

  it('displays memory list when loaded', async () => {
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

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMemories
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/test memory content/i)).toBeInTheDocument();
    });
  });

  it('has refresh button', () => {
    render(<MemoryPanel />);

    const refreshButton = screen.getByTitle(/refresh/i);
    expect(refreshButton).toBeInTheDocument();
  });

  it('has memory type filter', () => {
    render(<MemoryPanel />);

    const filterSelect = screen.getByRole('combobox');
    expect(filterSelect).toBeInTheDocument();
  });

  it('filters memories by type', async () => {
    const mockMemories = {
      memories: [
        { id: '1', type: 'short_term', content: 'Short term' },
        { id: '2', type: 'long_term', content: 'Long term' }
      ],
      total: 2
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMemories
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/short term/i)).toBeInTheDocument();
    });

    // Change filter
    const filterSelect = screen.getByRole('combobox');
    await fireEvent.change(filterSelect, { target: { value: 'long_term' } });

    // Should filter results
    await waitFor(() => {
      expect(screen.queryByText(/short term/i)).not.toBeInTheDocument();
    });
  });

  it('searches memories', async () => {
    const mockMemories = {
      memories: [
        { id: '1', type: 'short_term', content: 'Python programming' },
        { id: '2', type: 'long_term', content: 'Java programming' }
      ],
      total: 2
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMemories
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/python programming/i)).toBeInTheDocument();
    });

    // Search
    const searchInput = screen.getByPlaceholderText(/search memories/i);
    await fireEvent.change(searchInput, { target: { value: 'Python' } });

    // Should filter results
    await waitFor(() => {
      expect(screen.getByText(/python programming/i)).toBeInTheDocument();
    });
  });

  it('displays error message when API fails', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'));

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  it('deletes memory when delete button clicked', async () => {
    const mockMemories = {
      memories: [
        { id: '1', type: 'short_term', content: 'To delete' }
      ],
      total: 1
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMemories
    });

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/to delete/i)).toBeInTheDocument();
    });

    // Click delete
    const deleteButton = screen.getByTitle(/delete memory/i);
    await fireEvent.click(deleteButton);

    // Should call delete API
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2);
    });
  });

  it('displays memory timestamp', async () => {
    const mockMemories = {
      memories: [
        {
          id: '1',
          type: 'short_term',
          timestamp: '2024-01-01T12:00:00',
          content: 'Test'
        }
      ],
      total: 1
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMemories
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/2024/i)).toBeInTheDocument();
    });
  });
});
