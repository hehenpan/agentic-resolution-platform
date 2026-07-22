import { describe, it, expect, vi, beforeEach } from 'vitest';
import { chatService } from './chatService';

describe('chatService', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sends turn payload to /api/v1/chat/message without backend server', async () => {
    const mockResponse = {
      run_id: 'run_123',
      thread_id: 'thread_123',
      status: 'pending',
    };

    // Mock global fetch API
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
