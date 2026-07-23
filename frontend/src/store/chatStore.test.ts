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

  it('fetchSessionMessages maps history items into ChatMessage state', async () => {
    const mockItems = [
      {
        id: 1,
        event_id: 'evt_101',
        chat_session_id: 'cs_101',
        thread_id: 'thread_1',
        run_id: 'run_1',
        sender_type: 1,
        event_kind: 'user_message',
        sequence: 0,
        payload_json: JSON.stringify({ content: 'User question' }),
        create_ts_ms: 1753236000000,
      },
      {
        id: 2,
        event_id: 'evt_102',
        chat_session_id: 'cs_101',
        thread_id: 'thread_1',
        run_id: 'run_1',
        sender_type: 2,
        event_kind: 'agent.output_produced',
        sequence: 1,
        payload_json: JSON.stringify({ output: { parts: [{ text: 'Agent response' }] } }),
        create_ts_ms: 1753236001000,
      },
    ];

    vi.spyOn(chatService, 'listSessionMessages').mockResolvedValueOnce({
      code: 0,
      message: 'Success',
      data: {
        has_more: false,
        next_cursor: null,
        items: mockItems,
      },
    });

    await useChatStore.getState().fetchSessionMessages('cs_101');

    const messages = useChatStore.getState().sessionMessages['cs_101'];
    expect(messages).toHaveLength(2);
    expect(messages[0].role).toBe('user');
    expect(messages[0].content).toBe('User question');
    expect(messages[1].role).toBe('assistant');
    expect(messages[1].content).toBe('Agent response');
  });

  it('sendMessageStream handles SSE stream events and error status', async () => {
    vi.spyOn(chatService, 'sendSessionMessageStream').mockImplementation(
      async (_sessionId, _content, onMessage, _onError, onClose) => {
        onMessage('agent.output_produced', {
          output: { parts: [{ text: 'Chunk 1 ' }] },
        });
        onMessage('agent.output_produced', {
          output: { parts: [{ text: 'Chunk 2' }] },
        });
        onMessage('agent.run_completed', { kind: 'agent.run_completed' });
        if (onClose) onClose();
      }
    );

    await useChatStore.getState().sendMessageStream('cs_101', 'Test message');

    const messages = useChatStore.getState().sessionMessages['cs_101'];
    expect(messages).toHaveLength(2);
    expect(messages[0].role).toBe('user');
    expect(messages[0].content).toBe('Test message');
    expect(messages[1].role).toBe('assistant');
    expect(messages[1].content).toBe('Chunk 1 Chunk 2');
    expect(messages[1].status).toBe('completed');
    expect(useChatStore.getState().isStreaming).toBe(false);
  });
});

