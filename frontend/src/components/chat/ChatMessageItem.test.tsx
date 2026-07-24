import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ChatMessageItem } from './ChatMessageItem';
import type { ChatMessage } from '../../types/chat';
import { useAuthStore } from '../../store/authStore';

describe('ChatMessageItem Component', () => {
  it('renders user message with logged-in user email correctly', () => {
    useAuthStore.setState({ userEmail: 'agent_user@company.com' });

    const userMsg: ChatMessage = {
      id: 'msg_1',
      role: 'user',
      content: 'Process order refund',
      timestamp: new Date().toISOString(),
    };

    render(<ChatMessageItem message={userMsg} />);
    expect(screen.getByText('agent_user@company.com')).toBeInTheDocument();
    expect(screen.getByText('Process order refund')).toBeInTheDocument();
  });

  it('renders assistant message with tool execution badges', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_2',
      role: 'assistant',
      content: 'Refund completed successfully.',
      timestamp: new Date().toISOString(),
      toolCalls: [
        {
          name: 'refund_api',
          args: { amount: 100 },
          result: 'Status 200 OK',
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);
    expect(screen.getByText('Agent Assistant')).toBeInTheDocument();
    expect(screen.getByText('Refund completed successfully.')).toBeInTheDocument();
    expect(screen.getByText('Tool Execution Log')).toBeInTheDocument();
    expect(screen.getByText('fn: refund_api()')).toBeInTheDocument();
  });

  it('renders markdown content as formatted HTML for text messages', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_3',
      role: 'assistant',
      content: '## Refund Summary\n\n- Status: **approved**\n- Amount: `$100`',
      timestamp: new Date().toISOString(),
    };

    render(<ChatMessageItem message={agentMsg} />);

    expect(screen.getByRole('heading', { name: 'Refund Summary', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('approved').tagName).toBe('STRONG');
    expect(screen.getByText('$100').tagName).toBe('CODE');
    expect(screen.queryByText('## Refund Summary')).not.toBeInTheDocument();
  });

  it('renders a spinner instead of an empty assistant message bubble while waiting for first response', () => {
    const pendingAgentMsg: ChatMessage = {
      id: 'msg_4',
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      status: 'streaming',
    };

    render(<ChatMessageItem message={pendingAgentMsg} />);

    expect(screen.getByLabelText('Waiting for assistant response')).toBeInTheDocument();
    expect(screen.getByText('Agent Assistant')).toBeInTheDocument();
    expect(screen.queryByText('Failed to send or process message')).not.toBeInTheDocument();
  });
});
