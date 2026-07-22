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
