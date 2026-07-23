/** Strong TypeScript interfaces matching backend models */

export type AgentRunStatus = 'pending' | 'running' | 'success' | 'error' | 'interrupted';

export enum ChatSessionStatus {
  INVALID = 0,
  ACTIVE = 1,
  CLOSED = 2,
}

export interface ChatSessionMeta {
  id?: number | null;
  chat_session_id: string;
  tenant_id: number;
  user_id: number;
  title: string;
  status: ChatSessionStatus;
  create_ts: number;
  update_ts: number;
}

export interface CreateChatSessionRequest {
  title?: string | null;
}

export interface CreateChatSessionData {
  chat_session_id: string;
  session_info: ChatSessionMeta;
}

export interface CreateChatSessionResponse {
  code: number;
  message: string;
  data: CreateChatSessionData;
}

export interface ChatSessionListResponseData {
  has_more: boolean;
  next_cursor?: string | null;
  items: ChatSessionMeta[];
}

export interface ChatSessionListResponse {
  code: number;
  message: string;
  data: ChatSessionListResponseData;
}

export interface UserMessageInput {
  content: string;
  metadata?: Record<string, unknown>;
}

export interface AgentTurnRequest {
  thread_id: string;
  message: UserMessageInput;
  run_id?: string | null;
}

export interface HumanInputResponse {
  action: 'approve' | 'reject' | 'submit';
  feedback?: string;
  data?: Record<string, unknown>;
}

export interface AgentResumeCursor {
  checkpoint_id?: string;
  node_name?: string;
}

export interface AgentResumeRequest {
  thread_id: string;
  interrupt_id: string;
  resume_cursor: AgentResumeCursor;
  response: HumanInputResponse;
  run_id?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  status?: 'sending' | 'streaming' | 'completed' | 'error' | 'interrupted';
  toolCalls?: Array<{
    name: string;
    args: Record<string, unknown>;
    result?: string;
  }>;
}

export enum ChatMessageSenderType {
  USER = 1,
  AGENT = 2,
  SYSTEM = 3,
}

export interface ChatMessageItem {
  id?: number | null;
  event_id: string;
  chat_session_id: string;
  thread_id: string;
  run_id: string;
  sender_type: ChatMessageSenderType;
  event_kind: string;
  sequence: number;
  payload_json: string;
  create_ts_ms: number;
}

export interface ChatMessageListResponseData {
  has_more: boolean;
  next_cursor?: string | null;
  items: ChatMessageItem[];
}

export interface ChatMessageListResponse {
  code: number;
  message: string;
  data: ChatMessageListResponseData;
}

export interface SendChatMessageRequest {
  content: string;
}

export enum ChatSSEEventType {
  USER_MESSAGE = 'user_message',
  OUTPUT_PRODUCED = 'agent.output_produced',
  PROGRESS_REPORTED = 'agent.progress_reported',
  HUMAN_INPUT_REQUESTED = 'agent.human_input_requested',
  RUN_COMPLETED = 'agent.run_completed',
  RUN_INTERRUPTED = 'agent.run_interrupted',
  RUN_FAILED = 'agent.run_failed',
  ERROR = 'error',
}

export interface ChatSSEEvent<T = Record<string, unknown>> {
  event_id: string;
  event_type: ChatSSEEventType | string;
  data: T;
}

export interface InterruptEventData {
  interrupt_id: string;
  thread_id: string;
  node_name: string;
  description?: string;
  options?: string[];
  checkpoint_id?: string;
}

export interface SSEStreamEvent {
  event: string;
  data: string;
}

export interface ChatSession {
  threadId: string;
  title: string;
  lastUpdated: string;
  messages: ChatMessage[];
  status: AgentRunStatus;
  activeInterrupt?: InterruptEventData | null;
}

