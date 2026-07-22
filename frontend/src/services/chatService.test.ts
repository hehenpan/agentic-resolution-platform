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
});
