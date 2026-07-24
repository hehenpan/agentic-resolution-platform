import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { WorkbenchPage } from './WorkbenchPage';
import { useChatStore } from '../store/chatStore';

describe('WorkbenchPage Component', () => {
  beforeEach(() => {
    useChatStore.setState({
      sessions: [],
      sessionMessages: {},
      activeChatSessionId: null,
      isStreaming: false,
      activeInterrupt: null,
    });
  });

  it('renders empty state UI when no chat session is selected', () => {
    render(<WorkbenchPage />);

    expect(screen.getByText('No Chat Session Selected')).toBeInTheDocument();
    expect(screen.getByText('Create New Session')).toBeInTheDocument();
  });

  it('renders active chat session details when selected', () => {
    useChatStore.setState({
      sessions: [
        {
          id: 1,
          chat_session_id: 'cs_selected_001',
          tenant_id: 1,
          user_id: 10,
          title: 'Active Resolution Session',
          status: 1,
          create_ts: 1753236000,
          update_ts: 1753236000,
        },
      ],
      sessionMessages: {
        cs_selected_001: [],
      },
      activeChatSessionId: 'cs_selected_001',
    });

    render(<WorkbenchPage />);

    expect(screen.queryByText('No Chat Session Selected')).not.toBeInTheDocument();
    expect(screen.getByText('Active Resolution Session')).toBeInTheDocument();
  });
});
