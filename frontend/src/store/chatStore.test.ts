import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChatStore } from './chatStore';
import { chatService } from '../services/chatService';

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.setState({
      sessions: [],
      sessionMessages: {},
      activeChatSessionId: null,
      isLoadingSessions: false,
      isStreaming: false,
      activeInterrupt: null,
      error: null,
    });
    vi.restoreAllMocks();
  });

  it('fetchSessions populates sessions list', async () => {
    const mockSessions = [
      {
        id: 1,
        chat_session_id: 'cs_101',
        tenant_id: 1,
        user_id: 10,
        title: 'Customer Refund Query',
        status: 1,
        create_ts: 1753236000,
        update_ts: 1753236000,
      },
    ];

    vi.spyOn(chatService, 'listSessions').mockResolvedValueOnce({
      code: 0,
      message: 'Success',
      data: {
        has_more: false,
        next_cursor: null,
        items: mockSessions,
      },
    });

    await useChatStore.getState().fetchSessions();

    expect(useChatStore.getState().sessions).toEqual(mockSessions);
    expect(useChatStore.getState().isLoadingSessions).toBe(false);
  });

  it('createSession appends new session and sets activeChatSessionId', async () => {
    const mockSessionInfo = {
      id: 2,
      chat_session_id: 'cs_102',
      tenant_id: 1,
      user_id: 10,
      title: 'New Resolution Workspace',
      status: 1,
      create_ts: 1753236000,
      update_ts: 1753236000,
    };

    vi.spyOn(chatService, 'createSession').mockResolvedValueOnce({
      code: 0,
      message: 'Success',
      data: {
        chat_session_id: 'cs_102',
        session_info: mockSessionInfo,
      },
    });

    const newId = await useChatStore.getState().createSession('New Resolution Workspace');

    expect(newId).toBe('cs_102');
    expect(useChatStore.getState().activeChatSessionId).toBe('cs_102');
    expect(useChatStore.getState().sessions[0]).toEqual(mockSessionInfo);
  });

  it('setActiveChatSession updates activeChatSessionId', () => {
    useChatStore.getState().setActiveChatSession('cs_999');
    expect(useChatStore.getState().activeChatSessionId).toBe('cs_999');

    useChatStore.getState().setActiveChatSession(null);
    expect(useChatStore.getState().activeChatSessionId).toBeNull();
  });
});
