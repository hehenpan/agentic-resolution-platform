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

export enum WebHumanInputSchemaId {
  UNKNOWN = 'unknown',
  GET_USER_INPUT_V1 = 'human_input.get_user.v1',
  GET_ORDERS_INPUT_V1 = 'human_input.get_orders.v1',
  GET_ORDER_DETAILS_INPUT_V1 = 'human_input.get_order_details.v1',
  GET_RETURNS_BY_ORDER_INPUT_V1 = 'human_input.get_returns_by_order.v1',
  GET_RETURNS_BY_CUSTOMER_INPUT_V1 = 'human_input.get_returns_by_customer.v1',
  CREATE_RETURN_REQUEST_INPUT_V1 = 'human_input.create_return_request.v1',
}

export enum WebStructuredDataSchemaId {
  UNKNOWN = 'unknown',
  RAG_FILE_IMPORT_RESULT_V1 = 'rag.file_import.result.v1',
  ECOMMERCE_USER_RESULT_V1 = 'ecommerce.user_result.v1',
  ECOMMERCE_ORDERS_RESULT_V1 = 'ecommerce.orders_result.v1',
  ECOMMERCE_ORDER_DETAILS_RESULT_V1 = 'ecommerce.order_details_result.v1',
  ECOMMERCE_RETURNS_BY_ORDER_RESULT_V1 = 'ecommerce.returns_by_order_result.v1',
  ECOMMERCE_RETURNS_BY_CUSTOMER_RESULT_V1 = 'ecommerce.returns_by_customer_result.v1',
  ECOMMERCE_CREATE_RETURN_RESULT_V1 = 'ecommerce.create_return_result.v1',
}

export interface ResumeChatMessageRequest {
  schema_id: WebHumanInputSchemaId | string;
  resume_payload: Record<string, unknown>;
  chat_session_id: string;
  thread_id: string;
  interrupt_id?: string | null;
}

export interface WebHumanInputRequest {
  prompt: string;
  schema_id: WebHumanInputSchemaId | string;
  input_schema?: Record<string, unknown>;
  context?: Record<string, unknown>;
  allowed_actions?: string[];
}

export interface WebHumanInputRequestedData {
  event_id: string;
  kind: 'agent.human_input_requested';
  thread_id: string;
  run_id: string;
  sequence?: number;
  interrupt_id: string;
  request: WebHumanInputRequest;
  resume_cursor?: {
    checkpoint_id: string;
    checkpoint_ns?: string;
    checkpoint_map?: Record<string, string>;
  };
}

export interface ECommerceUserOutput {
  exists: boolean;
  user_id?: number | null;
  email: string;
  user_name?: string | null;
}

export interface ECommerceOrderOutput {
  order_id: number;
  user_id: number;
  email: string;
  status: number;
  total_amount: number;
  created_ts: number;
}

export interface ECommerceOrdersOutput {
  customer_email: string;
  orders: ECommerceOrderOutput[];
}

export interface WebTextPart {
  kind: 'text';
  text: string;
}

export interface WebStructuredDataPart {
  kind: 'structured_data';
  schema_id: WebStructuredDataSchemaId | string;
  data: ECommerceUserOutput | ECommerceOrdersOutput | Record<string, unknown>;
}

export type WebAgentOutputPart = WebTextPart | WebStructuredDataPart;

export interface WebAgentOutput {
  output_id: string;
  parts: WebAgentOutputPart[];
  metadata?: Record<string, unknown>;
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
  humanInputRequest?: WebHumanInputRequestedData | null;
  structuredParts?: WebAgentOutputPart[];
}

export interface ChatSSEEvent<T = Record<string, unknown>> {
  event_id: string;
  event_type: ChatSSEEventType | string;
  data: T;
}

export interface InterruptEventData {
  interrupt_id: string;
  thread_id: string;
  node_name?: string;
  description?: string;
  options?: string[];
  checkpoint_id?: string;
  schema_id?: string;
  request?: WebHumanInputRequest;
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


