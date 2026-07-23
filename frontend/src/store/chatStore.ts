import { create } from 'zustand';
import type { ChatSessionMeta, ChatMessage, InterruptEventData } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatStoreState {
  sessions: ChatSessionMeta[];
  sessionMessages: Record<string, ChatMessage[]>;
  activeChatSessionId: string | null;
  isLoadingSessions: boolean;
  isStreaming: boolean;
  activeInterrupt: InterruptEventData | null;
  error: string | null;

  // Actions
  fetchSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<string | null>;
  fetchSessionMessages: (chatSessionId: string) => Promise<void>;
  sendMessageStream: (chatSessionId: string, content: string) => Promise<void>;
  setActiveChatSession: (chatSessionId: string | null) => void;
  addMessage: (chatSessionId: string, message: ChatMessage) => void;
  updateMessageContent: (chatSessionId: string, messageId: string, contentDelta: string) => void;
  setMessageStatus: (chatSessionId: string, messageId: string, status: ChatMessage['status']) => void;
  setStreaming: (isStreaming: boolean) => void;
  setActiveInterrupt: (interrupt: InterruptEventData | null) => void;
}

export const useChatStore = create<ChatStoreState>((set, get) => ({
  sessions: [],
  sessionMessages: {},
  activeChatSessionId: null,
  isLoadingSessions: false,
  isStreaming: false,
  activeInterrupt: null,
  error: null,

  fetchSessions: async () => {
    set({ isLoadingSessions: true, error: null });
    try {
      const res = await chatService.listSessions();
      if (res.code === 0 && res.data) {
        set({
          sessions: res.data.items || [],
          isLoadingSessions: false,
        });
      } else {
        set({ isLoadingSessions: false, error: res.message || 'Failed to list chat sessions' });
      }
    } catch (err: unknown) {
      set({
        isLoadingSessions: false,
      });
    }
  },

  createSession: async (title?: string): Promise<string | null> => {
    try {
      const res = await chatService.createSession(title);
      if (res.code === 0 && res.data?.session_info) {
        const meta = res.data.session_info;
        set((state) => ({
          sessions: [meta, ...state.sessions],
          activeChatSessionId: meta.chat_session_id,
          sessionMessages: {
            ...state.sessionMessages,
            [meta.chat_session_id]: [],
          },
        }));
        return meta.chat_session_id;
      }
      return null;
    } catch (err: unknown) {
      // Mock / fallback session creation
      const newSessionId = `cs_mock_${Date.now()}`;
      const newMeta: ChatSessionMeta = {
        id: Date.now(),
        chat_session_id: newSessionId,
        tenant_id: 1,
        user_id: 101,
        title: title || 'New Chat Session',
        status: 1,
        create_ts: Math.floor(Date.now() / 1000),
        update_ts: Math.floor(Date.now() / 1000),
      };
      set((state) => ({
        sessions: [newMeta, ...state.sessions],
        activeChatSessionId: newSessionId,
        sessionMessages: {
          ...state.sessionMessages,
          [newSessionId]: [],
        },
      }));
      return newSessionId;
    }
  },

  fetchSessionMessages: async (chatSessionId: string) => {
    try {
      const res = await chatService.listSessionMessages(chatSessionId);
      if (res.code === 0 && res.data?.items) {
        const mappedMessages: ChatMessage[] = res.data.items.map((item) => {
          let textContent = '';
          try {
            const parsed = JSON.parse(item.payload_json);
            if (typeof parsed === 'string') {
              textContent = parsed;
            } else if (parsed?.content) {
              textContent = String(parsed.content);
            } else if (parsed?.output?.parts?.[0]?.text) {
              textContent = String(parsed.output.parts[0].text);
            } else {
              textContent = item.payload_json;
            }
          } catch {
            textContent = item.payload_json;
          }

          let role: ChatMessage['role'] = 'assistant';
          if (item.sender_type === 1) {
            role = 'user';
          } else if (item.sender_type === 3) {
            role = 'system';
          }

          return {
            id: item.event_id || `msg_${item.id || Date.now()}`,
            role,
            content: textContent,
            timestamp: new Date(item.create_ts_ms).toISOString(),
            status: 'completed',
          };
        });

        set((state) => ({
          sessionMessages: {
            ...state.sessionMessages,
            [chatSessionId]: mappedMessages,
          },
        }));
      }
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to fetch session messages' });
    }
  },

  sendMessageStream: async (chatSessionId: string, content: string) => {
    const userMsgId = `user_${Date.now()}`;
    const agentMsgId = `agent_${Date.now()}`;

    const userMessage: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      status: 'completed',
    };

    const agentPlaceholder: ChatMessage = {
      id: agentMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      status: 'streaming',
    };

    get().addMessage(chatSessionId, userMessage);
    get().addMessage(chatSessionId, agentPlaceholder);
    set({ isStreaming: true, error: null });

    try {
      await chatService.sendSessionMessageStream(
        chatSessionId,
        content,
        (event, data) => {
          if (event === 'agent.output_produced' || event === 'output_produced') {
            let textPart = '';
            const output = data.output as { parts?: Array<{ text?: string }> } | undefined;
            if (output?.parts?.[0]?.text) {
              textPart = output.parts[0].text;
            } else if (typeof data.content === 'string') {
              textPart = data.content;
            } else if (typeof data.text === 'string') {
              textPart = data.text;
            }

            if (textPart) {
              get().updateMessageContent(chatSessionId, agentMsgId, textPart);
            }
          } else if (event === 'agent.run_completed' || event === 'run_completed') {
            get().setMessageStatus(chatSessionId, agentMsgId, 'completed');
          } else if (event === 'agent.run_interrupted' || event === 'run_interrupted') {
            get().setMessageStatus(chatSessionId, agentMsgId, 'interrupted');
            get().setActiveInterrupt(data as unknown as InterruptEventData);
          } else if (event === 'error') {
            const detailStr = (data.detail as string) || 'Stream encountered error';
            get().setMessageStatus(chatSessionId, agentMsgId, 'error');
            set({ error: detailStr });
          }
        },
        (err) => {
          get().setMessageStatus(chatSessionId, agentMsgId, 'error');
          set({ error: err.message, isStreaming: false });
        },
        () => {
          set({ isStreaming: false });
        }
      );
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to send chat message';
      get().setMessageStatus(chatSessionId, agentMsgId, 'error');
      set({ error: errorMsg, isStreaming: false });
    }
  },

  setActiveChatSession: (chatSessionId: string | null) => {
    set({ activeChatSessionId: chatSessionId });
  },

  addMessage: (chatSessionId: string, message: ChatMessage) => {
    set((state) => {
      const currentMsgs = state.sessionMessages[chatSessionId] || [];
      return {
        sessionMessages: {
          ...state.sessionMessages,
          [chatSessionId]: [...currentMsgs, message],
        },
      };
    });
  },

  updateMessageContent: (chatSessionId: string, messageId: string, contentDelta: string) => {
    set((state) => {
      const currentMsgs = state.sessionMessages[chatSessionId] || [];
      const updatedMsgs = currentMsgs.map((msg) => {
        if (msg.id !== messageId) return msg;
        return {
          ...msg,
          content: msg.content + contentDelta,
        };
      });
      return {
        sessionMessages: {
          ...state.sessionMessages,
          [chatSessionId]: updatedMsgs,
        },
      };
    });
  },

  setMessageStatus: (chatSessionId: string, messageId: string, status: ChatMessage['status']) => {
    set((state) => {
      const currentMsgs = state.sessionMessages[chatSessionId] || [];
      const updatedMsgs = currentMsgs.map((msg) => {
        if (msg.id !== messageId) return msg;
        return { ...msg, status };
      });
      return {
        sessionMessages: {
          ...state.sessionMessages,
          [chatSessionId]: updatedMsgs,
        },
      };
    });
  },

  setStreaming: (isStreaming: boolean) => set({ isStreaming }),
  setActiveInterrupt: (activeInterrupt: InterruptEventData | null) => set({ activeInterrupt }),
}));
