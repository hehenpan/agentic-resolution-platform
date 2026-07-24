import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { useChatStore } from '../../store/chatStore';

describe('Sidebar Component', () => {
  beforeEach(() => {
    useChatStore.setState({
      sessions: [],
      activeChatSessionId: null,
      isLoadingSessions: false,
    });
    vi.restoreAllMocks();
  });

  it('renders New Session button and fetches sessions on mount', () => {
    const fetchSpy = vi.fn();
    useChatStore.setState({ fetchSessions: fetchSpy });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('New Session')).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('renders list of sessions and handles session selection', () => {
    const setActiveSpy = vi.fn();
    useChatStore.setState({
      sessions: [
        {
          id: 1,
          chat_session_id: 'cs_101',
          tenant_id: 1,
          user_id: 10,
          title: 'Customer Refund Resolution',
          status: 1,
          create_ts: 1753236000,
          update_ts: 1753236000,
        },
      ],
      activeChatSessionId: null,
      setActiveChatSession: setActiveSpy,
    });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    const sessionItem = screen.getByText('Customer Refund Resolution');
    expect(sessionItem).toBeInTheDocument();

    fireEvent.click(sessionItem);
    expect(setActiveSpy).toHaveBeenCalledWith('cs_101');
  });

  it('triggers createSession when New Session button is clicked', async () => {
    const createSpy = vi.fn().mockResolvedValue('cs_999');
    useChatStore.setState({ createSession: createSpy });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    const newBtn = screen.getByRole('button', { name: /New Session/i });
    fireEvent.click(newBtn);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith('New Chat Session');
    });
  });
});
