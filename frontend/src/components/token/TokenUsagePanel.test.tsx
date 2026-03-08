// Test file

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { TokenUsagePanel } from '../components/token/TokenUsagePanel';

// Mock fetch API
global.fetch = vi.fn();

describe('TokenUsagePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders token usage panel with header', () => {
    render(<TokenUsagePanel />);

    expect(screen.getByText(/token/i)).toBeInTheDocument();
  });

  it('displays empty state when no usage data', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ usage: [], total: 0 })
    });

    render(<TokenUsagePanel />);

    await waitFor(() => {
      expect(screen.getByText(/no token usage data/i)).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    render(<TokenUsagePanel />);

    // Should show some loading indicator or empty state
    expect(screen.getByText(/token/i)).toBeInTheDocument();
  });

  it('displays token usage data when loaded', async () => {
    const mockUsage = {
      usage: [
        {
          date: '2024-01-01',
          model: 'claude-sonnet-4-20250514',
          input_tokens: 1000,
          output_tokens: 500,
          total_tokens: 1500
        }
      ],
      total: {
        input_tokens: 1000,
        output_tokens: 500,
        total_tokens: 1500
      }
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockUsage
    });

    render(<TokenUsagePanel />);

    await waitFor(() => {
      // Should display token data
      expect(screen.getByText(/total/i)).toBeInTheDocument();
    });
  });

  it('displays error message when API fails', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'));

    render(<TokenUsagePanel />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  it('has refresh button', () => {
    render(<TokenUsagePanel />);

    const refreshButton = screen.getByTitle(/refresh/i);
    expect(refreshButton).toBeInTheDocument();
  });

  it('has clear button', () => {
    render(<TokenUsagePanel />);

    const clearButton = screen.getByTitle(/clear token usage/i);
    expect(clearButton).toBeInTheDocument();
  });

  it('shows token breakdown by model', async () => {
    const mockUsage = {
      usage: [
        { model: 'claude-sonnet', input_tokens: 1000, output_tokens: 500 },
        { model: 'claude-opus', input_tokens: 2000, output_tokens: 1000 }
      ],
      total: { input_tokens: 3000, output_tokens: 1500, total_tokens: 4500 }
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockUsage
    });

    render(<TokenUsagePanel />);

    await waitFor(() => {
      // Should show model breakdown
      expect(screen.getByText(/claude/i)).toBeInTheDocument();
    });
  });
});
