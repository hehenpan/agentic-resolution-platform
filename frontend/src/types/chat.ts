/** Strong TypeScript interfaces matching backend models */

export type AgentRunStatus = 'pending' | 'running' | 'success' | 'error' | 'interrupted';

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
