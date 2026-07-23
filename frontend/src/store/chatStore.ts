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
  resumeSessionMessageStream: (
    chatSessionId: string,
    resumePayload: Record<string, unknown>,
    userDisplayContent?: string
  ) => Promise<void>;
  setActiveChatSession: (chatSessionId: string | null) => void;
  addMessage: (chatSessionId: string, message: ChatMessage) => void;
  updateMessageContent: (chatSessionId: string, messageId: string, contentDelta: string) => void;
  setMessageStatus: (chatSessionId: string, messageId: string, status: ChatMessage['status']) => void;
  setHumanInputRequest: (chatSessionId: string, messageId: string, humanInputReq: any) => void;
  addStructuredPart: (chatSessionId: string, messageId: string, part: any) => void;
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
            [chatSessionId]: mappedMessages.reverse(),
          },
        }));
      }
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to fetch session messages' });
    }
  },

  sendMessageStream: async (chatSessionId: string, content: string) => {
    const activeInterrupt = get().activeInterrupt;
    // If active interrupt exists, user input in chat box acts as resume using natural language (llm_text)
    if (activeInterrupt) {
      return get().resumeSessionMessageStream(chatSessionId, { llm_text: content }, content);
    }

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
          if (event === 'agent.human_input_requested' || event === 'human_input_requested') {
            const reqData = data as any;
            const interruptObj: InterruptEventData = {
              interrupt_id: reqData.interrupt_id || `int_${Date.now()}`,
              thread_id: reqData.thread_id || `thread_${chatSessionId}`,
              schema_id: reqData.request?.schema_id,
              description: reqData.request?.prompt,
              request: reqData.request,
            };
            get().setActiveInterrupt(interruptObj);
            get().setHumanInputRequest(chatSessionId, agentMsgId, reqData);
            get().setMessageStatus(chatSessionId, agentMsgId, 'interrupted');
          } else if (event === 'agent.output_produced' || event === 'output_produced') {
            const output = data.output as { parts?: Array<any> } | undefined;
            if (output?.parts && Array.isArray(output.parts)) {
              for (const part of output.parts) {
                if ((!part.kind || part.kind === 'text') && part.text) {
                  get().updateMessageContent(chatSessionId, agentMsgId, part.text);
                } else if (part.kind === 'structured_data') {
                  get().addStructuredPart(chatSessionId, agentMsgId, part);
                }
              }
            } else if (typeof data.content === 'string') {
              get().updateMessageContent(chatSessionId, agentMsgId, data.content);
            } else if (typeof data.text === 'string') {
              get().updateMessageContent(chatSessionId, agentMsgId, data.text);
            }
          } else if (event === 'agent.run_completed' || event === 'run_completed') {
            get().setMessageStatus(chatSessionId, agentMsgId, 'completed');
            set({ activeInterrupt: null });
          } else if (event === 'agent.run_interrupted' || event === 'run_interrupted') {
            get().setMessageStatus(chatSessionId, agentMsgId, 'interrupted');
            if (data.interrupt_ids && Array.isArray(data.interrupt_ids) && data.interrupt_ids[0]) {
              const current = get().activeInterrupt;
              if (current) {
                get().setActiveInterrupt({ ...current, interrupt_id: data.interrupt_ids[0] });
              }
            }
          } else if (event === 'error') {
            const detailStr = (data.detail as string) || 'Stream encountered error';
            get().setMessageStatus(chatSessionId, userMsgId, 'error');
            get().setMessageStatus(chatSessionId, agentMsgId, 'error');
            set({ error: detailStr });
          }
        },
        (err) => {
          get().setMessageStatus(chatSessionId, userMsgId, 'error');
          get().setMessageStatus(chatSessionId, agentMsgId, 'error');
          set({ error: err.message, isStreaming: false });
        },
        () => {
          set({ isStreaming: false });
        }
      );
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to send chat message';
      get().setMessageStatus(chatSessionId, userMsgId, 'error');
      get().setMessageStatus(chatSessionId, agentMsgId, 'error');
      set({ error: errorMsg, isStreaming: false });
    }
  },

  resumeSessionMessageStream: async (
    chatSessionId: string,
    resumePayload: Record<string, unknown>,
    userDisplayContent?: string
  ) => {
    const activeInterrupt = get().activeInterrupt;
    const interruptId = activeInterrupt?.interrupt_id || `int_mock_${Date.now()}`;
    const schemaId = activeInterrupt?.schema_id || activeInterrupt?.request?.schema_id || 'human_input.get_user.v1';

    const userMsgId = `user_resume_${Date.now()}`;
    const agentMsgId = `agent_resume_${Date.now()}`;

    // Text displayed in user chat bubble
    const userText =
      userDisplayContent ||
      (resumePayload.email
        ? `[Resume Form] email: ${resumePayload.email}`
        : resumePayload.llm_text
        ? String(resumePayload.llm_text)
        : JSON.stringify(resumePayload));

    const userMessage: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: userText,
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
    // Clear active interrupt once resume is initiated
    set({ activeInterrupt: null, isStreaming: true, error: null });

    try {
      await chatService.resumeSessionMessageStream(
        chatSessionId,
        {
          schema_id: schemaId,
          resume_payload: resumePayload,
          chat_session_id: chatSessionId,
          thread_id: activeInterrupt?.thread_id || `thread_${chatSessionId}`,
          interrupt_id: interruptId,
        },
        (event, data) => {
          if (event === 'agent.output_produced' || event === 'output_produced') {
            const output = data.output as { parts?: Array<any> } | undefined;
            if (output?.parts && Array.isArray(output.parts)) {
              for (const part of output.parts) {
                if (part.kind === 'text' && part.text) {
                  get().updateMessageContent(chatSessionId, agentMsgId, part.text);
                } else if (part.kind === 'structured_data') {
                  get().addStructuredPart(chatSessionId, agentMsgId, part);
                }
              }
            } else if (typeof data.content === 'string') {
              get().updateMessageContent(chatSessionId, agentMsgId, data.content);
            }
          } else if (event === 'agent.run_completed' || event === 'run_completed') {
            get().setMessageStatus(chatSessionId, agentMsgId, 'completed');
          } else if (event === 'error') {
            const detailStr = (data.detail as string) || 'Resume stream encountered error';
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
      const errorMsg = err instanceof Error ? err.message : 'Failed to resume chat message';
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

  setHumanInputRequest: (chatSessionId: string, messageId: string, humanInputReq: any) => {
    set((state) => {
      const currentMsgs = state.sessionMessages[chatSessionId] || [];
      const updatedMsgs = currentMsgs.map((msg) => {
        if (msg.id !== messageId) return msg;
        return { ...msg, humanInputRequest: humanInputReq };
      });
      return {
        sessionMessages: {
          ...state.sessionMessages,
          [chatSessionId]: updatedMsgs,
        },
      };
    });
  },

  addStructuredPart: (chatSessionId: string, messageId: string, part: any) => {
    set((state) => {
      const currentMsgs = state.sessionMessages[chatSessionId] || [];
      const updatedMsgs = currentMsgs.map((msg) => {
        if (msg.id !== messageId) return msg;
        const currentParts = msg.structuredParts || [];
        return { ...msg, structuredParts: [...currentParts, part] };
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
