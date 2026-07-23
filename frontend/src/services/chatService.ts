import { request } from './httpClient';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type {
  AgentTurnRequest,
  AgentResumeRequest,
  ChatSession,
  CreateChatSessionResponse,
  ChatSessionListResponse,
  ChatMessageListResponse,
  SendChatMessageRequest,
  ResumeChatMessageRequest,
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

  /** Query chat history messages for session (GET /api/v1/chat/sessions/{chat_session_id}/messages) */
  async listSessionMessages(
    chatSessionId: string,
    limit = 50,
    cursor?: string
  ): Promise<ChatMessageListResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (cursor) {
      params.append('cursor', cursor);
    }
    return request<ChatMessageListResponse>(
      `/api/v1/chat/sessions/${chatSessionId}/messages?${params.toString()}`,
      { method: 'GET' }
    );
  },

  /**
   * Send message in chat session and stream response via SSE
   * (POST /api/v1/chat/sessions/{chat_session_id}/messages)
   *
   * Form 1: If pre-stream validation fails, server returns HTTP status error (e.g. 400/500)
   * with application/json body.
   * Form 2: If success, server returns 200 OK with text/event-stream content type and SSE event payload.
   */
  async sendSessionMessageStream(
    chatSessionId: string,
    content: string,
    onMessage: (event: string, data: Record<string, unknown>) => void,
    onError?: (err: Error) => void,
    onClose?: () => void,
    signal?: AbortSignal
  ) {
    const payload: SendChatMessageRequest = { content };
    await fetchEventSource(`/api/v1/chat/sessions/${chatSessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
      async onopen(response) {
        const contentType = response.headers.get('content-type') || '';
        if (response.ok && contentType.includes('text/event-stream')) {
          return;
        }

        // Form 1: Pre-stream check failed (HTTP status error with JSON or plain text body)
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorJson = await response.json();
          if (errorJson && typeof errorJson.detail === 'string') {
            errorMessage = errorJson.detail;
          } else if (errorJson && typeof errorJson.message === 'string') {
            errorMessage = errorJson.message;
          }
        } catch {
          // Fallback to HTTP status message if body parsing fails
        }
        throw new Error(errorMessage);
      },
      onmessage(ev) {
        let parsedData: Record<string, unknown> = {};
        if (ev.data) {
          try {
            parsedData = JSON.parse(ev.data);
          } catch {
            parsedData = { raw: ev.data };
          }
        }
        onMessage(ev.event || 'message', parsedData);
      },
      onerror(err) {
        if (onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
        throw err;
      },
      onclose() {
        if (onClose) {
          onClose();
        }
      },
    });
  },

  /**
   * Resume an interrupted chat session turn and stream response via SSE
   * (POST /api/v1/chat/sessions/{chat_session_id}/resume)
   */
  async resumeSessionMessageStream(
    chatSessionId: string,
    resumeReq: ResumeChatMessageRequest,
    onMessage: (event: string, data: Record<string, unknown>) => void,
    onError?: (err: Error) => void,
    onClose?: () => void,
    signal?: AbortSignal
  ) {
    await fetchEventSource(`/api/v1/chat/sessions/${chatSessionId}/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(resumeReq),
      signal,
      async onopen(response) {
        const contentType = response.headers.get('content-type') || '';
        if (response.ok && contentType.includes('text/event-stream')) {
          return;
        }

        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorJson = await response.json();
          if (errorJson && typeof errorJson.detail === 'string') {
            errorMessage = errorJson.detail;
          } else if (errorJson && typeof errorJson.message === 'string') {
            errorMessage = errorJson.message;
          }
        } catch {
          // Fallback to HTTP status message
        }
        throw new Error(errorMessage);
      },
      onmessage(ev) {
        let parsedData: Record<string, unknown> = {};
        if (ev.data) {
          try {
            parsedData = JSON.parse(ev.data);
          } catch {
            parsedData = { raw: ev.data };
          }
        }
        onMessage(ev.event || 'message', parsedData);
      },
      onerror(err) {
        if (onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
        throw err;
      },
      onclose() {
        if (onClose) {
          onClose();
        }
      },
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

