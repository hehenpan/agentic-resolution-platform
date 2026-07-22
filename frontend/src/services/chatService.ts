import { request } from './httpClient';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type {
  AgentTurnRequest,
  AgentResumeRequest,
  ChatSession,
  CreateChatSessionResponse,
  ChatSessionListResponse,
} from '../types/chat';

export const chatService = {
  /** Create a new chat session database record (POST /api/v1/chat/sessions) */
  async createSession(title?: string): Promise<CreateChatSessionResponse> {
    return request<CreateChatSessionResponse>('/api/v1/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({
        title: title || 'New Chat',
      }),
    });
  },

  /** Query chat sessions metadata list for logged-in user (GET /api/v1/chat/sessions) */
  async listSessions(limit = 50, cursor?: string): Promise<ChatSessionListResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (cursor) {
      params.append('cursor', cursor);
    }
    return request<ChatSessionListResponse>(`/api/v1/chat/sessions?${params.toString()}`, {
      method: 'GET',
    });
  },

  /** Post a user message turn */
  async sendTurn(payload: AgentTurnRequest) {
    return request<{ run_id: string; thread_id: string; status: string }>(
      '/api/v1/chat/message',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /** Resume an interrupted agent turn */
  async resumeInterrupt(payload: AgentResumeRequest) {
    return request<{ run_id: string; thread_id: string; status: string }>(
      '/api/v1/chat/resume',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /** Stream SSE events for a chat turn */
  async streamTurn(
    payload: AgentTurnRequest,
    onMessage: (event: string, data: string) => void,
    onError: (err: Error) => void,
    onClose: () => void,
    signal?: AbortSignal
  ) {
    await fetchEventSource('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
      onopen(response) {
        if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
          return Promise.resolve();
        }
        throw new Error(`Failed to open SSE stream: ${response.statusText}`);
      },
      onmessage(ev) {
        onMessage(ev.event || 'message', ev.data);
      },
      onerror(err) {
        onError(err instanceof Error ? err : new Error(String(err)));
      },
      onclose() {
        onClose();
      },
    });
  },

  /** Mock session getter for template workbench */
  async getSessions(): Promise<ChatSession[]> {
    return [
      {
        threadId: 'thread_demo_001',
        title: 'Policy QA & Customer Refund Resolution',
        lastUpdated: new Date().toISOString(),
        status: 'success',
        messages: [
          {
            id: 'msg_1',
            role: 'user',
            content: 'Check policy for order #88412 and process refund request.',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            status: 'completed',
          },
          {
            id: 'msg_2',
            role: 'assistant',
            content: 'Order #88412 qualifies for full refund under Policy Sec 4.2. Action logged.',
            timestamp: new Date(Date.now() - 3500000).toISOString(),
            status: 'completed',
            toolCalls: [
              {
                name: 'retrieve_policy',
                args: { order_id: '88412' },
                result: 'Policy matched: 30-day return policy valid.',
              },
            ],
          },
        ],
      },
    ];
  },
};
