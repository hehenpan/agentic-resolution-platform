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
});
