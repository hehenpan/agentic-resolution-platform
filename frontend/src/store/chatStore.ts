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
