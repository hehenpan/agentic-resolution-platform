import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChatStore } from './chatStore';
import { chatService } from '../services/chatService';

describe('chatStore', () => {
  beforeEach(() => {
    vi.useRealTimers();
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
        id: 3,
        event_id: 'evt_103',
        chat_session_id: 'cs_101',
        thread_id: 'thread_1',
        run_id: 'run_1',
        sender_type: 2,
        event_kind: 'agent.run_completed',
        sequence: 2,
        payload_json: JSON.stringify({ kind: 'agent.run_completed' }),
        create_ts_ms: 1753236002000,
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

  it('sendMessageStream clears waiting state when the first visible assistant response arrives', async () => {
    let resolveStream: () => void = () => undefined;

    vi.spyOn(chatService, 'sendSessionMessageStream').mockImplementation(
      async (_sessionId, _content, onMessage, _onError, onClose) => {
        onMessage('agent.output_produced', {
          output: { parts: [{ text: 'First response chunk.' }] },
        });

        await new Promise<void>((resolve) => {
          resolveStream = resolve;
        });
        onMessage('agent.run_completed', { kind: 'agent.run_completed' });
        if (onClose) onClose();
      }
    );

    const sendPromise = useChatStore.getState().sendMessageStream('cs_101', 'Test message');
    await Promise.resolve();

    const messages = useChatStore.getState().sessionMessages['cs_101'];
    expect(messages[1].content).toBe('First response chunk.');
    expect(useChatStore.getState().isStreaming).toBe(false);

    resolveStream();
    await sendPromise;
  });

  it('sendMessageStream times out if no visible assistant response arrives', async () => {
    vi.useFakeTimers();

    vi.spyOn(chatService, 'sendSessionMessageStream').mockImplementation(
      async (_sessionId, _content, _onMessage, _onError, _onClose, signal) => {
        await new Promise<void>((resolve) => {
          signal?.addEventListener('abort', () => resolve(), { once: true });
        });
      }
    );

    const sendPromise = useChatStore.getState().sendMessageStream('cs_101', 'Test message');
    await Promise.resolve();

    expect(useChatStore.getState().isStreaming).toBe(true);

    vi.advanceTimersByTime(60_000);
    await sendPromise;

    const messages = useChatStore.getState().sessionMessages['cs_101'];
    expect(messages[1].role).toBe('assistant');
    expect(messages[1].content).toBe('Agent response timed out. Please try again.');
    expect(messages[1].status).toBe('error');
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it('sendMessageStream ignores repeated visible SSE events with the same event_id', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-07-23T10:00:00.000Z'));
    const createdAt = Date.parse('2025-07-23T10:00:01.000Z') / 1000;

    vi.spyOn(chatService, 'sendSessionMessageStream').mockImplementation(
      async (_sessionId, _content, onMessage, _onError, onClose) => {
        onMessage('agent.output_produced', {
          event_id: 'evt_duplicate_output',
          created_at: createdAt,
          output: { parts: [{ kind: 'text', text: 'First visible response.' }] },
        });
        onMessage('agent.output_produced', {
          event_id: 'evt_duplicate_output',
          created_at: createdAt + 1,
          output: { parts: [{ kind: 'text', text: 'Duplicate response should not render.' }] },
        });
        onMessage('agent.run_completed', { kind: 'agent.run_completed' });
        if (onClose) onClose();
      }
    );

    await useChatStore.getState().sendMessageStream('cs_101', 'Test message');

    const messages = useChatStore.getState().sessionMessages['cs_101'];
    expect(messages).toHaveLength(2);
    expect(messages[1].role).toBe('assistant');
    expect(messages[1].eventId).toBe('evt_duplicate_output');
    expect(messages[1].content).toBe('First visible response.');
    expect(messages[1].content).not.toContain('Duplicate response');
    expect(messages[1].timestamp).toBe('2025-07-23T10:00:01.000Z');
  });

  it('sendMessageStream inserts visible SSE messages by event timestamp', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-07-23T10:00:10.000Z'));
    const outputCreatedAt = Date.parse('2025-07-23T10:00:15.000Z') / 1000;

    useChatStore.setState({
      sessionMessages: {
        cs_101: [
          {
            id: 'existing_later',
            role: 'system',
            content: 'Existing later message',
            timestamp: '2025-07-23T10:00:20.000Z',
            status: 'completed',
          },
        ],
      },
    });

    vi.spyOn(chatService, 'sendSessionMessageStream').mockImplementation(
      async (_sessionId, _content, onMessage, _onError, onClose) => {
        onMessage('agent.output_produced', {
          event_id: 'evt_ordered_output',
          created_at: outputCreatedAt,
          output: { parts: [{ kind: 'text', text: 'Timestamp ordered response.' }] },
        });
        onMessage('agent.run_completed', { kind: 'agent.run_completed' });
        if (onClose) onClose();
      }
    );

    await useChatStore.getState().sendMessageStream('cs_101', 'User at ten seconds');

    const messages = useChatStore.getState().sessionMessages['cs_101'];
    expect(messages.map((message) => message.content)).toEqual([
      'User at ten seconds',
      'Timestamp ordered response.',
      'Existing later message',
    ]);
    expect(messages.map((message) => message.timestamp)).toEqual([
      '2025-07-23T10:00:10.000Z',
      '2025-07-23T10:00:15.000Z',
      '2025-07-23T10:00:20.000Z',
    ]);
  });

  it('resumeSessionMessageStream calls chatService.resumeSessionMessageStream and updates state', async () => {
    vi.spyOn(chatService, 'resumeSessionMessageStream').mockImplementation(
      async (_sessionId, _req, onMessage, _onError, onClose) => {
        onMessage('agent.output_produced', {
          output: {
            parts: [
              { kind: 'text', text: 'Retrieved user info.' },
              {
                kind: 'structured_data',
                schema_id: 'ecommerce.user_result.v1',
                data: { exists: true, email: 'alex@example.com' },
              },
            ],
          },
        });
        onMessage('agent.run_completed', { kind: 'agent.run_completed' });
        if (onClose) onClose();
      }
    );

    useChatStore.setState({
      activeInterrupt: {
        interrupt_id: 'intr_1001',
        thread_id: 'thread_1001',
        schema_id: 'human_input.get_user.v1',
      },
    });

    await useChatStore.getState().resumeSessionMessageStream('cs_101', { email: 'alex@example.com' });

    const messages = useChatStore.getState().sessionMessages['cs_101'];
    expect(messages).toHaveLength(2);
    expect(messages[0].role).toBe('user');
    expect(messages[0].content).toContain('alex@example.com');
    expect(messages[1].role).toBe('assistant');
    expect(messages[1].content).toBe('Retrieved user info.');
    expect(messages[1].structuredParts).toEqual([
      {
        kind: 'structured_data',
        schema_id: 'ecommerce.user_result.v1',
        data: { exists: true, email: 'alex@example.com' },
      },
    ]);
    expect(useChatStore.getState().activeInterrupt).toBeNull();
  });

  it('sendMessageStream automatically delegates to resumeSessionMessageStream when activeInterrupt is set', async () => {
    const resumeSpy = vi
      .spyOn(chatService, 'resumeSessionMessageStream')
      .mockImplementation(async (_sessionId, _req, _onMessage, _onError, onClose) => {
        if (onClose) onClose();
      });

    useChatStore.setState({
      activeInterrupt: {
        interrupt_id: 'intr_1002',
        thread_id: 'thread_1002',
        schema_id: 'human_input.get_orders.v1',
      },
    });

    await useChatStore.getState().sendMessageStream('cs_101', 'Natural language text for resume');

    expect(resumeSpy).toHaveBeenCalledWith(
      'cs_101',
      expect.objectContaining({
        schema_id: 'human_input.get_orders.v1',
        resume_payload: { llm_text: 'Natural language text for resume' },
      }),
      expect.any(Function),
      expect.any(Function),
      expect.any(Function),
      expect.any(AbortSignal)
    );
  });
});
