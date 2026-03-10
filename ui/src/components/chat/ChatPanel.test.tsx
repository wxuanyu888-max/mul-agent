// Test file

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatPanel } from './ChatPanel';

// Mock fetch API
global.fetch = vi.fn();

describe('ChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chat panel with empty state', () => {
    render(<ChatPanel />);

    expect(screen.getByText(/chat/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument();
  });

  it('displays empty state message when no messages', () => {
    render(<ChatPanel />);

    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument();
  });

  it('allows typing in message input', async () => {
    render(<ChatPanel />);

    const textarea = screen.getByPlaceholderText(/type your message/i);
    await fireEvent.change(textarea, { target: { value: 'Test message' } });

    expect(textarea).toHaveValue('Test message');
  });

  it('sends message and displays it in chat', async () => {
    // Mock successful API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ response: 'Hello! How can I help?', conversation_id: 'default' })
    });

    render(<ChatPanel />);

    const textarea = screen.getByPlaceholderText(/type your message/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    await fireEvent.change(textarea, { target: { value: 'Hello' } });
    await fireEvent.click(sendButton);

    // User message should appear
    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
    });
  });

  it('shows loading state while waiting for response', async () => {
    // Mock delayed API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => new Promise(resolve =>
        setTimeout(() => resolve({ response: 'Response', conversation_id: 'default' }), 100)
      )
    });

    render(<ChatPanel />);

    const textarea = screen.getByPlaceholderText(/type your message/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    await fireEvent.change(textarea, { target: { value: 'Test' } });
    await fireEvent.click(sendButton);

    // Loading indicator should appear
    await waitFor(() => {
      expect(screen.getByText(/agent is thinking/i)).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('displays error message when API fails', async () => {
    // Mock failed API response
    fetch.mockRejectedValueOnce(new Error('Network error'));

    render(<ChatPanel />);

    const textarea = screen.getByPlaceholderText(/type your message/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    await fireEvent.change(textarea, { target: { value: 'Test' } });
    await fireEvent.click(sendButton);

    // Error message should appear
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('clears chat when clear button clicked', async () => {
    render(<ChatPanel />);

    const clearButton = screen.getByTitle(/clear chat/i);
    await fireEvent.click(clearButton);

    // Should show empty state
    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument();
  });

  it('displays agent selector', () => {
    render(<ChatPanel />);

    const agentSelector = screen.getByRole('combobox');
    expect(agentSelector).toBeInTheDocument();
  });

  it('has refresh button', () => {
    render(<ChatPanel />);

    const refreshButton = screen.getByTitle(/refresh/i);
    expect(refreshButton).toBeInTheDocument();
  });

  it('handles enter key to send message (without shift)', async () => {
    render(<ChatPanel />);

    const textarea = screen.getByPlaceholderText(/type your message/i);

    await fireEvent.change(textarea, { target: { value: 'Test message' } });
    await fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    // Message should be sent
    await waitFor(() => {
      expect(screen.getByText('Test message')).toBeInTheDocument();
    });
  });

  it('allows new line with shift+enter', async () => {
    render(<ChatPanel />);

    const textarea = screen.getByPlaceholderText(/type your message/i);

    await fireEvent.change(textarea, { target: { value: 'Line 1' } });
    await fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    // Should still have the value (not sent)
    expect(textarea).toHaveValue('Line 1');
  });
});
