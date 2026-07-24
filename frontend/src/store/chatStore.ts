import { create } from 'zustand';
import type {
  ChatSessionMeta,
  ChatMessage,
  ChatMessageItem,
  InterruptEventData,
  WebAgentOutputPart,
  WebHumanInputRequestedData,
} from '../types/chat';
import { chatService } from '../services/chatService';

const AGENT_RUN_COMPLETED_KIND = 'agent.run_completed';
const ASSISTANT_RESPONSE_TIMEOUT_MS = 60_000;
const ASSISTANT_RESPONSE_TIMEOUT_MESSAGE =
  'Agent response timed out. Please try again.';

const parsePayloadJson = (payloadJson: string): unknown => {
  try {
    return JSON.parse(payloadJson);
  } catch {
    return null;
  }
};

const getPayloadKind = (payload: unknown): string | null => {
  if (!payload || typeof payload !== 'object' || !('kind' in payload)) {
    return null;
  }

  const kind = (payload as { kind?: unknown }).kind;
  return typeof kind === 'string' ? kind : null;
};

const shouldDisplayHistoryItem = (item: ChatMessageItem): boolean => {
  if (item.event_kind === AGENT_RUN_COMPLETED_KIND) {
    return false;
  }

  return getPayloadKind(parsePayloadJson(item.payload_json)) !== AGENT_RUN_COMPLETED_KIND;
};

const getFirstOutputText = (payload: unknown): string | null => {
  if (!payload || typeof payload !== 'object' || !('output' in payload)) {
    return null;
  }

  const output = (payload as { output?: { parts?: unknown } }).output;
  if (!Array.isArray(output?.parts)) {
    return null;
  }

  const firstText = (output.parts[0] as { text?: unknown } | undefined)?.text;
  return typeof firstText === 'string' ? firstText : null;
};

const getHistoryMessageContent = (item: ChatMessageItem): string => {
  const parsed = parsePayloadJson(item.payload_json);
  if (typeof parsed === 'string') {
    return parsed;
  }

  if (parsed && typeof parsed === 'object' && 'content' in parsed) {
    return String((parsed as { content: unknown }).content);
  }

  return getFirstOutputText(parsed) ?? item.payload_json;
};

const parseTimestampMs = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value > 1_000_000_000_000 ? value : value * 1000;
  }

  if (typeof value !== 'string' || !value.trim()) {
    return null;
  }

  const numericValue = Number(value);
  if (Number.isFinite(numericValue)) {
    return numericValue > 1_000_000_000_000 ? numericValue : numericValue * 1000;
  }

  const parsedDate = Date.parse(value);
  return Number.isFinite(parsedDate) ? parsedDate : null;
};

const getEventId = (data: Record<string, unknown>): string | null => {
  const eventId = data.event_id;
  return typeof eventId === 'string' && eventId.trim() ? eventId : null;
};

const getEventTimestamp = (data: Record<string, unknown>): string => {
  const timestampMs =
    parseTimestampMs(data.created_at) ??
    parseTimestampMs(data.create_ts_ms) ??
    parseTimestampMs(data.timestamp) ??
    Date.now();

  return new Date(timestampMs).toISOString();
};

const getCurrentMessageTimestamp = (): string => {
  return new Date(Math.floor(Date.now() / 1000) * 1000).toISOString();
};

const getMessageTimestampMs = (message: ChatMessage): number => {
  const timestampMs = Date.parse(message.timestamp);
  return Number.isFinite(timestampMs) ? timestampMs : 0;
};

const hasDisplayedEventId = (messages: ChatMessage[], eventId: string): boolean => {
  return messages.some((message) => message.id === eventId || message.eventId === eventId);
};

const sortMessagesChronologically = (messages: ChatMessage[]): ChatMessage[] => {
  return messages
    .map((message, index) => ({ message, index }))
    .sort((left, right) => {
      const timeDiff = getMessageTimestampMs(left.message) - getMessageTimestampMs(right.message);
      if (timeDiff !== 0) {
        return timeDiff;
      }
      return left.index - right.index;
    })
    .map(({ message }) => message);
};

const dedupeAndSortMessages = (messages: ChatMessage[]): ChatMessage[] => {
  const seenEventIds = new Set<string>();
  const uniqueMessages: ChatMessage[] = [];

  for (const message of messages) {
    const eventId = message.eventId ?? message.id;
    if (eventId && seenEventIds.has(eventId)) {
      continue;
    }
    if (eventId) {
      seenEventIds.add(eventId);
    }
    uniqueMessages.push(message);
  }

  return sortMessagesChronologically(uniqueMessages);
};

const appendMessageChronologically = (
  messages: ChatMessage[],
  message: ChatMessage
): ChatMessage[] => {
  if (hasDisplayedEventId(messages, message.eventId ?? message.id)) {
    return messages;
  }

  return sortMessagesChronologically([...messages, message]);
};

const getOutputParts = (data: Record<string, unknown>): unknown[] => {
  const output = data.output;
  if (!output || typeof output !== 'object' || !('parts' in output)) {
    return [];
  }

  const parts = (output as { parts?: unknown }).parts;
  return Array.isArray(parts) ? parts : [];
};

const getAssistantOutputUpdate = (
  data: Record<string, unknown>
): Pick<AssistantStreamEventUpdate, 'contentDelta' | 'structuredParts'> => {
  const parts = getOutputParts(data);
  let contentDelta = '';
  const structuredParts: WebAgentOutputPart[] = [];

  for (const part of parts) {
    if (!part || typeof part !== 'object') {
      continue;
    }

    const candidate = part as { kind?: unknown; text?: unknown };
    if ((!candidate.kind || candidate.kind === 'text') && typeof candidate.text === 'string') {
      contentDelta += candidate.text;
    } else if (candidate.kind === 'structured_data') {
      structuredParts.push(part as WebAgentOutputPart);
    }
  }

  if (!contentDelta && typeof data.content === 'string') {
    contentDelta = data.content;
  } else if (!contentDelta && typeof data.text === 'string') {
    contentDelta = data.text;
  }

  return { contentDelta, structuredParts };
};

const hasVisibleAssistantUpdate = (update: AssistantStreamEventUpdate): boolean => {
  return Boolean(
    update.contentDelta ||
      update.humanInputRequest ||
      (update.structuredParts && update.structuredParts.length > 0)
  );
};

const getMessageById = (
  messagesBySession: Record<string, ChatMessage[]>,
  chatSessionId: string,
  messageId: string
): ChatMessage | undefined => {
  return messagesBySession[chatSessionId]?.find((message) => message.id === messageId);
};

interface AssistantStreamEventUpdate {
  eventId: string | null;
  timestamp: string;
  contentDelta?: string;
  structuredParts?: WebAgentOutputPart[];
  humanInputRequest?: WebHumanInputRequestedData;
  status?: ChatMessage['status'];
}

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
  replaceMessageContent: (chatSessionId: string, messageId: string, content: string) => void;
  setHumanInputRequest: (chatSessionId: string, messageId: string, humanInputReq: any) => void;
  addStructuredPart: (chatSessionId: string, messageId: string, part: any) => void;
  applyAssistantStreamEvent: (
    chatSessionId: string,
    placeholderMessageId: string,
    update: AssistantStreamEventUpdate
  ) => boolean;
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
        const mappedMessages: ChatMessage[] = res.data.items.filter(shouldDisplayHistoryItem).map((item) => {
          const textContent = getHistoryMessageContent(item);

          let role: ChatMessage['role'] = 'assistant';
          if (item.sender_type === 1) {
            role = 'user';
          } else if (item.sender_type === 3) {
            role = 'system';
          }

          return {
            id: item.event_id || `msg_${item.id || Date.now()}`,
            eventId: item.event_id,
            role,
            content: textContent,
            timestamp: new Date(item.create_ts_ms).toISOString(),
            status: 'completed',
          };
        });

        set((state) => ({
          sessionMessages: {
            ...state.sessionMessages,
            [chatSessionId]: dedupeAndSortMessages(mappedMessages),
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
      timestamp: getCurrentMessageTimestamp(),
      status: 'completed',
    };

    const agentPlaceholder: ChatMessage = {
      id: agentMsgId,
      role: 'assistant',
      content: '',
      timestamp: getCurrentMessageTimestamp(),
      status: 'streaming',
    };

    get().addMessage(chatSessionId, userMessage);
    get().addMessage(chatSessionId, agentPlaceholder);
    set({ isStreaming: true, error: null });

    const abortController = new AbortController();
    let hasReceivedAssistantResponse = false;
    let didTimeout = false;

    const markAssistantResponseReceived = () => {
      if (hasReceivedAssistantResponse) {
        return;
      }
      hasReceivedAssistantResponse = true;
      window.clearTimeout(responseTimeoutId);
      set({ isStreaming: false });
    };

    const responseTimeoutId = window.setTimeout(() => {
      didTimeout = true;
      abortController.abort();
      get().replaceMessageContent(chatSessionId, agentMsgId, ASSISTANT_RESPONSE_TIMEOUT_MESSAGE);
      get().setMessageStatus(chatSessionId, agentMsgId, 'error');
      set({ error: ASSISTANT_RESPONSE_TIMEOUT_MESSAGE, isStreaming: false });
    }, ASSISTANT_RESPONSE_TIMEOUT_MS);

    try {
      await chatService.sendSessionMessageStream(
        chatSessionId,
        content,
        (event, data) => {
          if (event === 'agent.human_input_requested' || event === 'human_input_requested') {
            const reqData = data as unknown as WebHumanInputRequestedData;
            const applied = get().applyAssistantStreamEvent(chatSessionId, agentMsgId, {
              eventId: getEventId(data),
              timestamp: getEventTimestamp(data),
              humanInputRequest: reqData,
              status: 'interrupted',
            });
            if (!applied) {
              return;
            }
            markAssistantResponseReceived();
            const interruptObj: InterruptEventData = {
              interrupt_id: reqData.interrupt_id || `int_${Date.now()}`,
              thread_id: reqData.thread_id || `thread_${chatSessionId}`,
              schema_id: reqData.request?.schema_id,
              description: reqData.request?.prompt,
              request: reqData.request,
            };
            get().setActiveInterrupt(interruptObj);
          } else if (event === 'agent.output_produced' || event === 'output_produced') {
            const outputUpdate = getAssistantOutputUpdate(data);
            const update = {
              eventId: getEventId(data),
              timestamp: getEventTimestamp(data),
              contentDelta: outputUpdate.contentDelta,
              structuredParts: outputUpdate.structuredParts,
              status: 'streaming',
            } satisfies AssistantStreamEventUpdate;
            get().applyAssistantStreamEvent(chatSessionId, agentMsgId, update);
            if (hasVisibleAssistantUpdate(update)) {
              markAssistantResponseReceived();
            }
          } else if (event === 'agent.run_completed' || event === 'run_completed') {
            window.clearTimeout(responseTimeoutId);
            const agentMessage = getMessageById(get().sessionMessages, chatSessionId, agentMsgId);
            if (!hasReceivedAssistantResponse && !agentMessage?.content) {
              get().replaceMessageContent(chatSessionId, agentMsgId, 'Agent completed without a visible response.');
            }
            get().setMessageStatus(chatSessionId, agentMsgId, 'completed');
            set({ activeInterrupt: null, isStreaming: false });
          } else if (event === 'agent.run_interrupted' || event === 'run_interrupted') {
            window.clearTimeout(responseTimeoutId);
            get().setMessageStatus(chatSessionId, agentMsgId, 'interrupted');
            set({ isStreaming: false });
            if (data.interrupt_ids && Array.isArray(data.interrupt_ids) && data.interrupt_ids[0]) {
              const current = get().activeInterrupt;
              if (current) {
                get().setActiveInterrupt({ ...current, interrupt_id: data.interrupt_ids[0] });
              }
            }
          } else if (event === 'error') {
            window.clearTimeout(responseTimeoutId);
            const detailStr = (data.detail as string) || 'Stream encountered error';
            get().setMessageStatus(chatSessionId, userMsgId, 'error');
            get().setMessageStatus(chatSessionId, agentMsgId, 'error');
            set({ error: detailStr, isStreaming: false });
          }
        },
        (err) => {
          if (didTimeout) {
            return;
          }
          window.clearTimeout(responseTimeoutId);
          get().setMessageStatus(chatSessionId, userMsgId, 'error');
          get().setMessageStatus(chatSessionId, agentMsgId, 'error');
          set({ error: err.message, isStreaming: false });
        },
        () => {
          window.clearTimeout(responseTimeoutId);
          set({ isStreaming: false });
        },
        abortController.signal
      );
    } catch (err: unknown) {
      if (didTimeout) {
        return;
      }
      window.clearTimeout(responseTimeoutId);
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
      timestamp: getCurrentMessageTimestamp(),
      status: 'completed',
    };

    const agentPlaceholder: ChatMessage = {
      id: agentMsgId,
      role: 'assistant',
      content: '',
      timestamp: getCurrentMessageTimestamp(),
      status: 'streaming',
    };

    get().addMessage(chatSessionId, userMessage);
    get().addMessage(chatSessionId, agentPlaceholder);
    // Clear active interrupt once resume is initiated
    set({ activeInterrupt: null, isStreaming: true, error: null });

    const abortController = new AbortController();
    let hasReceivedAssistantResponse = false;
    let didTimeout = false;

    const markAssistantResponseReceived = () => {
      if (hasReceivedAssistantResponse) {
        return;
      }
      hasReceivedAssistantResponse = true;
      window.clearTimeout(responseTimeoutId);
      set({ isStreaming: false });
    };

    const responseTimeoutId = window.setTimeout(() => {
      didTimeout = true;
      abortController.abort();
      get().replaceMessageContent(chatSessionId, agentMsgId, ASSISTANT_RESPONSE_TIMEOUT_MESSAGE);
      get().setMessageStatus(chatSessionId, agentMsgId, 'error');
      set({ error: ASSISTANT_RESPONSE_TIMEOUT_MESSAGE, isStreaming: false });
    }, ASSISTANT_RESPONSE_TIMEOUT_MS);

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
            const outputUpdate = getAssistantOutputUpdate(data);
            const update = {
              eventId: getEventId(data),
              timestamp: getEventTimestamp(data),
              contentDelta: outputUpdate.contentDelta,
              structuredParts: outputUpdate.structuredParts,
              status: 'streaming',
            } satisfies AssistantStreamEventUpdate;
            get().applyAssistantStreamEvent(chatSessionId, agentMsgId, update);
            if (hasVisibleAssistantUpdate(update)) {
              markAssistantResponseReceived();
            }
          } else if (event === 'agent.run_completed' || event === 'run_completed') {
            window.clearTimeout(responseTimeoutId);
            const agentMessage = getMessageById(get().sessionMessages, chatSessionId, agentMsgId);
            if (!hasReceivedAssistantResponse && !agentMessage?.content) {
              get().replaceMessageContent(chatSessionId, agentMsgId, 'Agent completed without a visible response.');
            }
            get().setMessageStatus(chatSessionId, agentMsgId, 'completed');
            set({ isStreaming: false });
          } else if (event === 'error') {
            window.clearTimeout(responseTimeoutId);
            const detailStr = (data.detail as string) || 'Resume stream encountered error';
            get().setMessageStatus(chatSessionId, agentMsgId, 'error');
            set({ error: detailStr, isStreaming: false });
          }
        },
        (err) => {
          if (didTimeout) {
            return;
          }
          window.clearTimeout(responseTimeoutId);
          get().setMessageStatus(chatSessionId, agentMsgId, 'error');
          set({ error: err.message, isStreaming: false });
        },
        () => {
          window.clearTimeout(responseTimeoutId);
          set({ isStreaming: false });
        },
        abortController.signal
      );
    } catch (err: unknown) {
      if (didTimeout) {
        return;
      }
      window.clearTimeout(responseTimeoutId);
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
          [chatSessionId]: appendMessageChronologically(currentMsgs, message),
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

  replaceMessageContent: (chatSessionId: string, messageId: string, content: string) => {
    set((state) => {
      const currentMsgs = state.sessionMessages[chatSessionId] || [];
      const updatedMsgs = currentMsgs.map((msg) => {
        if (msg.id !== messageId) return msg;
        return {
          ...msg,
          content,
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

  applyAssistantStreamEvent: (
    chatSessionId: string,
    placeholderMessageId: string,
    update: AssistantStreamEventUpdate
  ): boolean => {
    let applied = false;

    set((state) => {
      const currentMsgs = state.sessionMessages[chatSessionId] || [];
      if (update.eventId && hasDisplayedEventId(currentMsgs, update.eventId)) {
        return state;
      }

      const placeholderIndex = currentMsgs.findIndex(
        (message) =>
          message.id === placeholderMessageId &&
          (!message.eventId || message.eventId === update.eventId)
      );
      const contentDelta = update.contentDelta ?? '';
      const structuredParts = update.structuredParts ?? [];

      const applyUpdate = (message: ChatMessage): ChatMessage => ({
        ...message,
        eventId: update.eventId ?? message.eventId,
        timestamp: update.timestamp,
        content: message.content + contentDelta,
        status: update.status ?? message.status,
        humanInputRequest: update.humanInputRequest ?? message.humanInputRequest,
        structuredParts:
          structuredParts.length > 0
            ? [...(message.structuredParts || []), ...structuredParts]
            : message.structuredParts,
      });

      const nextMessages =
        placeholderIndex >= 0
          ? currentMsgs.map((message, index) =>
              index === placeholderIndex ? applyUpdate(message) : message
            )
          : [
              ...currentMsgs,
              {
                id: update.eventId ?? `agent_${Date.now()}`,
                eventId: update.eventId ?? undefined,
                role: 'assistant' as const,
                content: contentDelta,
                timestamp: update.timestamp,
                status: update.status ?? 'streaming',
                humanInputRequest: update.humanInputRequest,
                structuredParts: structuredParts.length > 0 ? structuredParts : undefined,
              },
            ];

      applied = true;
      return {
        sessionMessages: {
          ...state.sessionMessages,
          [chatSessionId]: sortMessagesChronologically(nextMessages),
        },
      };
    });

    return applied;
  },

  setStreaming: (isStreaming: boolean) => set({ isStreaming }),
  setActiveInterrupt: (activeInterrupt: InterruptEventData | null) => set({ activeInterrupt }),
}));
