// TokenUsagePanel Test Suite

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import TokenUsagePanel from './TokenUsagePanel';
import { tokenUsageApi, infoApi } from '../../services/api';

// Mock API modules
vi.mock('../../services/api', () => ({
  tokenUsageApi: {
    getAll: vi.fn(),
    get: vi.fn(),
  },
  infoApi: {
    getFilesBatch: vi.fn(),
  },
}));

describe('TokenUsagePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders token usage panel with header', async () => {
    vi.mocked(tokenUsageApi.getAll).mockResolvedValue({
      data: { all_usage: {} }
    });

    await act(async () => {
      render(<TokenUsagePanel />);
    });

    expect(screen.getByText(/Token 使用统计/i)).toBeInTheDocument();
  });

  it('displays loading state initially', async () => {
    vi.mocked(tokenUsageApi.getAll).mockResolvedValue({
      data: { all_usage: {} }
    });

    await act(async () => {
      render(<TokenUsagePanel />);
    });

    expect(screen.getByText(/Token 使用统计/i)).toBeInTheDocument();
  });

  it('displays empty state when no agents', async () => {
    vi.mocked(tokenUsageApi.getAll).mockResolvedValue({
      data: { all_usage: {} }
    });

    await act(async () => {
      render(<TokenUsagePanel />);
    });

    await waitFor(() => {
      expect(screen.getByText(/暂无数据/i)).toBeInTheDocument();
    });
  });

  it('displays token usage data when loaded', async () => {
    const mockAllUsage = {
      test_agent: {
        input_tokens: 1000,
        output_tokens: 500,
        total_tokens: 1500,
        access_count: 10,
        last_access_time: '2024-01-01T00:00:00Z'
      }
    };

    vi.mocked(tokenUsageApi.getAll).mockResolvedValue({
      data: { all_usage: mockAllUsage }
    });

    // Mock get to return empty logs to avoid errors
    vi.mocked(tokenUsageApi.get).mockResolvedValue({
      data: { llm_logs: [] }
    } as any);

    await act(async () => {
      render(<TokenUsagePanel />);
    });

    await waitFor(() => {
      expect(screen.getByText(/test_agent/i)).toBeInTheDocument();
      // Use getAllByText since total appears in both row and footer
      const totalElements = screen.getAllByText(/1,500/i);
      expect(totalElements.length).toBeGreaterThan(0);
    });
  });

  it('displays error message when API fails', async () => {
    vi.mocked(tokenUsageApi.getAll).mockRejectedValue(new Error('Network error'));

    await act(async () => {
      render(<TokenUsagePanel />);
    });

    await waitFor(() => {
      expect(screen.getByText(/加载 Token 使用数据失败/i)).toBeInTheDocument();
    });
  });

  it('renders table headers correctly', async () => {
    vi.mocked(tokenUsageApi.getAll).mockResolvedValue({
      data: { all_usage: {} }
    });

    await act(async () => {
      render(<TokenUsagePanel />);
    });

    expect(screen.getByText(/输入 Token/i)).toBeInTheDocument();
    expect(screen.getByText(/输出 Token/i)).toBeInTheDocument();
    expect(screen.getByText(/总 Token/i)).toBeInTheDocument();
  });
});
