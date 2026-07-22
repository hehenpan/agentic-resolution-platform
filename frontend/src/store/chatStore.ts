import { create } from 'zustand';
import type { ChatSession, ChatMessage, InterruptEventData } from '../types/chat';

interface ChatStoreState {
  sessions: ChatSession[];
  activeThreadId: string;
  isStreaming: boolean;
  activeInterrupt: InterruptEventData | null;
  
  // Actions
  setActiveThread: (threadId: string) => void;
  createNewThread: () => string;
  addMessage: (threadId: string, message: ChatMessage) => void;
  updateMessageContent: (threadId: string, messageId: string, contentDelta: string) => void;
  setMessageStatus: (threadId: string, messageId: string, status: ChatMessage['status']) => void;
  setStreaming: (isStreaming: boolean) => void;
  setActiveInterrupt: (interrupt: InterruptEventData | null) => void;
  setSessions: (sessions: ChatSession[]) => void;
}

export const useChatStore = create<ChatStoreState>((set) => ({
  sessions: [
    {
      threadId: 'thread_demo_001',
      title: 'Policy QA & Resolution Workbench',
      lastUpdated: new Date().toISOString(),
      status: 'success',
      messages: [
        {
          id: 'msg_1',
          role: 'user',
          content: 'Hello, please review refund order #99182.',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          status: 'completed',
        },
        {
          id: 'msg_2',
          role: 'assistant',
          content: 'I have retrieved the policy for order #99182. All conditions are satisfied.',
          timestamp: new Date(Date.now() - 3500000).toISOString(),
          status: 'completed',
          toolCalls: [
            {
              name: 'query_policy_db',
              args: { order_id: '99182' },
              result: 'Found active return window (14 days remaining).',
            },
          ],
        },
      ],
    },
  ],
  activeThreadId: 'thread_demo_001',
  isStreaming: false,
  activeInterrupt: null,

  setActiveThread: (threadId) => set({ activeThreadId: threadId }),

  createNewThread: () => {
    const newThreadId = `thread_${Date.now()}`;
    const newSession: ChatSession = {
      threadId: newThreadId,
      title: 'New Resolution Workspace',
      lastUpdated: new Date().toISOString(),
      status: 'pending',
      messages: [],
    };
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      activeThreadId: newThreadId,
    }));
    return newThreadId;
  },

  addMessage: (threadId, message) => {
    set((state) => ({
      sessions: state.sessions.map((session) => {
        if (session.threadId !== threadId) return session;
        return {
          ...session,
          lastUpdated: new Date().toISOString(),
          messages: [...session.messages, message],
        };
      }),
    }));
  },

  updateMessageContent: (threadId, messageId, contentDelta) => {
    set((state) => ({
      sessions: state.sessions.map((session) => {
        if (session.threadId !== threadId) return session;
        return {
          ...session,
          messages: session.messages.map((msg) => {
            if (msg.id !== messageId) return msg;
            return {
              ...msg,
              content: msg.content + contentDelta,
            };
          }),
        };
      }),
    }));
  },

  setMessageStatus: (threadId, messageId, status) => {
    set((state) => ({
      sessions: state.sessions.map((session) => {
        if (session.threadId !== threadId) return session;
        return {
          ...session,
          messages: session.messages.map((msg) => {
            if (msg.id !== messageId) return msg;
            return { ...msg, status };
          }),
        };
      }),
    }));
  },

  setStreaming: (isStreaming) => set({ isStreaming }),
  setActiveInterrupt: (activeInterrupt) => set({ activeInterrupt }),
  setSessions: (sessions) => set({ sessions }),
}));
