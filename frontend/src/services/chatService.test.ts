import { describe, it, expect, vi, beforeEach } from 'vitest';
import { chatService } from './chatService';

describe('chatService', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('calls POST /api/v1/chat/sessions when createSession is called', async () => {
    const mockResponse = {
      code: 0,
      message: 'Chat session created successfully',
      data: {
        chat_session_id: 'cs_1001',
        session_info: {
          id: 1,
          chat_session_id: 'cs_1001',
          tenant_id: 1,
          user_id: 101,
          title: 'New Resolution Workspace',
          status: 1,
          create_ts: 1753236000,
          update_ts: 1753236000,
        },
      },
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => mockResponse,
      })
    );

    const result = await chatService.createSession('New Resolution Workspace');

    expect(fetch).toHaveBeenCalledWith('/api/v1/chat/sessions', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ title: 'New Resolution Workspace' }),
    }));
    expect(result).toEqual(mockResponse);
  });

  it('calls GET /api/v1/chat/sessions when listSessions is called', async () => {
    const mockResponse = {
      code: 0,
      message: 'Chat sessions retrieved successfully',
      data: {
        has_more: false,
        next_cursor: null,
        items: [
          {
            id: 1,
            chat_session_id: 'cs_1001',
            tenant_id: 1,
            user_id: 101,
            title: 'Resolution Session 1',
            status: 1,
            create_ts: 1753236000,
            update_ts: 1753236000,
          },
        ],
      },
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })
    );

    const result = await chatService.listSessions(50);

    expect(fetch).toHaveBeenCalledWith('/api/v1/chat/sessions?limit=50', expect.objectContaining({
      method: 'GET',
    }));
    expect(result).toEqual(mockResponse);
  });

  it('calls GET /api/v1/chat/sessions/{chat_session_id}/messages when listSessionMessages is called', async () => {
    const mockResponse = {
      code: 0,
      message: 'Chat history messages retrieved successfully',
      data: {
        has_more: false,
        next_cursor: null,
        items: [
          {
            id: 1,
            event_id: 'evt_101',
            chat_session_id: 'cs_1001',
            thread_id: 'thread_1',
            run_id: 'run_1',
            sender_type: 1,
            event_kind: 'user_message',
            sequence: 0,
            payload_json: '{"content": "Hello"}',
            create_ts_ms: 1753236000000,
          },
        ],
      },
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })
    );

    const result = await chatService.listSessionMessages('cs_1001', 50);

    expect(fetch).toHaveBeenCalledWith('/api/v1/chat/sessions/cs_1001/messages?limit=50', expect.objectContaining({
      method: 'GET',
    }));
    expect(result).toEqual(mockResponse);
  });

  it('handles POST /api/v1/chat/sessions/{chat_session_id}/messages Form 1: HTTP status error with JSON detail', async () => {
    const mockErrorResponse = {
      detail: 'Chat session not found or access denied',
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockErrorResponse,
      })
    );

    const onError = vi.fn();
    const onMessage = vi.fn();

    await expect(
      chatService.sendSessionMessageStream(
        'invalid_session',
        'Hello',
        onMessage,
        onError
      )
    ).rejects.toThrow('Chat session not found or access denied');

    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'Chat session not found or access denied',
      })
    );
    expect(onMessage).not.toHaveBeenCalled();
  });

  it('handles POST /api/v1/chat/sessions/{chat_session_id}/messages Form 2: HTTP 200 text/event-stream SSE events', async () => {
    const sseBody = [
      'event: user_message\n',
      'data: {"event_id":"evt_1","kind":"user_message","content":"Hello AI"}\n\n',
      'event: agent.output_produced\n',
      'data: {"event_id":"evt_2","kind":"agent.output_produced","output":{"parts":[{"text":"Hello human!"}]}}\n\n',
      'event: agent.run_completed\n',
      'data: {"event_id":"evt_3","kind":"agent.run_completed"}\n\n',
    ].join('');

    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sseBody));
        controller.close();
      },
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: new Headers({ 'content-type': 'text/event-stream' }),
        body: stream,
      })
    );

    const onMessage = vi.fn();
    const onError = vi.fn();
    const onClose = vi.fn();

    await chatService.sendSessionMessageStream(
      'cs_1001',
      'Hello AI',
      onMessage,
      onError,
      onClose
    );

    expect(onMessage).toHaveBeenCalledWith(
      'user_message',
      expect.objectContaining({ content: 'Hello AI' })
    );
    expect(onMessage).toHaveBeenCalledWith(
      'agent.output_produced',
      expect.objectContaining({
        output: { parts: [{ text: 'Hello human!' }] },
      })
    );
    expect(onMessage).toHaveBeenCalledWith(
      'agent.run_completed',
      expect.objectContaining({ kind: 'agent.run_completed' })
    );
    expect(onClose).toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  it('sends turn payload to /api/v1/chat/message without backend server', async () => {
    const mockResponse = {
      run_id: 'run_123',
      thread_id: 'thread_123',
      status: 'pending',
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })
    );

    const result = await chatService.sendTurn({
      thread_id: 'thread_123',
      message: { content: 'Test question' },
    });

    expect(fetch).toHaveBeenCalledWith('/api/v1/chat/message', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        thread_id: 'thread_123',
        message: { content: 'Test question' },
      }),
    }));
    expect(result).toEqual(mockResponse);
  });

  it('streams SSE events for resumeSessionMessageStream to /api/v1/chat/sessions/:id/resume', async () => {
    const ssePayload = [
      'event: agent.output_produced\ndata: {"kind":"agent.output_produced","output":{"parts":[{"kind":"structured_data","schema_id":"ecommerce.user_result.v1","data":{"exists":true,"user_id":1001,"email":"alex@example.com","user_name":"Alex"}}]}}\n\n',
      'event: agent.run_completed\ndata: {"kind":"agent.run_completed"}\n\n',
    ].join('');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload));
        controller.close();
      },
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'text/event-stream' }),
        body: stream,
      })
    );

    const onMessage = vi.fn();
    const onError = vi.fn();
    const onClose = vi.fn();

    await chatService.resumeSessionMessageStream(
      'cs_1001',
      {
        schema_id: 'human_input.get_user.v1',
        resume_payload: { email: 'alex@example.com' },
        chat_session_id: 'cs_1001',
        thread_id: 'thread_1001',
        interrupt_id: 'intr_1001',
      },
      onMessage,
      onError,
      onClose
    );

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/chat/sessions/cs_1001/resume',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          schema_id: 'human_input.get_user.v1',
          resume_payload: { email: 'alex@example.com' },
          chat_session_id: 'cs_1001',
          thread_id: 'thread_1001',
          interrupt_id: 'intr_1001',
        }),
      })
    );
    expect(onMessage).toHaveBeenCalledWith(
      'agent.output_produced',
      expect.objectContaining({
        kind: 'agent.output_produced',
      })
    );
    expect(onClose).toHaveBeenCalled();
  });
});


