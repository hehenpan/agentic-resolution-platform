import React from 'react';
import { Bot, User, Wrench, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type {
  ChatMessage,
  ECommerceUserOutput,
  ECommerceOrdersOutput,
  ECommerceOrderDetailsOutput,
  ECommerceReturnsByOrderOutput,
  ECommerceReturnsByCustomerOutput,
  ECommerceCreateReturnOutput,
} from '../../types/chat';
import { useAuthStore } from '../../store/authStore';
import { useChatStore } from '../../store/chatStore';
import { InterruptTabCard } from './InterruptTabCard';
import { UserInfoCard } from './UserInfoCard';
import { OrdersCard } from './OrdersCard';
import { OrderDetailsCard } from './OrderDetailsCard';
import { ReturnsByOrderCard } from './ReturnsByOrderCard';
import { ReturnsByCustomerCard } from './ReturnsByCustomerCard';
import { CreateReturnResultCard } from './CreateReturnResultCard';

interface ChatMessageItemProps {
  message: ChatMessage;
}

const markdownPattern =
  /(^|\n)(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|```|\|.+\|)|(\*\*[^*\n]+\*\*)|(__[^_\n]+__)|(`[^`\n]+`)|(\[[^\]\n]+\]\([^)]+\))/;

const markdownComponents: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  h1: ({ children }) => <h1 className="mb-2 text-lg font-semibold leading-snug">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-2 text-base font-semibold leading-snug">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-2 text-sm font-semibold leading-snug">{children}</h3>,
  ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 text-left last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 text-left last:mb-0">{children}</ol>,
  li: ({ children }) => <li className="pl-1">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-border pl-3 text-muted-foreground">{children}</blockquote>
  ),
  a: ({ children, href }) => (
    <a className="font-medium underline underline-offset-2" href={href} rel="noreferrer" target="_blank">
      {children}
    </a>
  ),
  code: ({ children, className }) => (
    <code className={`rounded bg-muted/70 px-1 py-0.5 font-mono text-[0.85em] ${className ?? ''}`}>
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg bg-muted/70 p-3 text-left text-xs leading-relaxed">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="min-w-full border-collapse text-left text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border border-border px-2 py-1 font-semibold">{children}</th>,
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
};

interface MessageContentProps {
  content: string;
}

const MessageContent: React.FC<MessageContentProps> = ({ content }) => {
  if (!markdownPattern.test(content)) {
    return <div className="whitespace-pre-wrap">{content}</div>;
  }

  return (
    <div className="markdown-message max-w-none text-left">
      <ReactMarkdown components={markdownComponents} remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
};

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message }) => {
  const { userEmail } = useAuthStore();
  const { activeChatSessionId, sessionMessages, resumeSessionMessageStream } = useChatStore();

  const currentMessages = activeChatSessionId ? (sessionMessages[activeChatSessionId] || []) : [];
  const hasMsg = currentMessages.some((msg) => msg.id === message.id);
  const isLatestMessage = hasMsg
    ? currentMessages[currentMessages.length - 1]?.id === message.id
    : true;

  const isUser = message.role === 'user';
  const isError = message.status === 'error';
  const userName = userEmail || 'Customer Support';
  const hasVisibleAssistantPayload =
    Boolean(message.content) ||
    Boolean(message.humanInputRequest) ||
    Boolean(message.structuredParts && message.structuredParts.length > 0);
  const isWaitingForAssistantResponse =
    !isUser && message.status === 'streaming' && !hasVisibleAssistantPayload;

  const handleInterruptSubmit = (payload: Record<string, unknown>, displayContent?: string) => {
    if (activeChatSessionId) {
      resumeSessionMessageStream(activeChatSessionId, payload, displayContent);
    }
  };

  return (
    <div className={`flex space-x-3 max-w-4xl ${isUser ? 'ml-auto flex-row-reverse space-x-reverse' : ''}`}>
      <div
        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-md ${
          isError
            ? 'bg-red-500/20 text-red-400 border border-red-500/40'
            : isUser
            ? 'bg-blue-600 text-white'
            : 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
        }`}
      >
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      <div className={`flex-1 space-y-2 ${isUser ? 'text-right' : ''}`}>
        <div className={`flex items-center space-x-2 text-xs text-muted-foreground mb-1 ${isUser ? 'justify-end' : ''}`}>
          {isUser ? (
            <>
              {isError && <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />}
              <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
              <span>•</span>
              <span className="font-semibold text-foreground">{userName}</span>
            </>
          ) : (
            <>
              <span className="font-semibold text-foreground">Agent Assistant</span>
              <span>•</span>
              <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
              {isError && <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />}
            </>
          )}
        </div>

        {isWaitingForAssistantResponse ? (
          <div className="inline-flex items-center rounded-full border border-border bg-muted/30 px-3 py-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-label="Waiting for assistant response" />
          </div>
        ) : (
          <div
            className={`inline-block p-4 rounded-2xl text-sm leading-relaxed ${
              isError
                ? 'bg-red-500/10 border border-red-500/40 text-foreground rounded-2xl'
                : isUser
                ? 'bg-blue-600 text-white rounded-tr-none shadow-lg shadow-blue-500/10'
                : 'glass-panel text-foreground rounded-tl-none border border-border'
            }`}
          >
            {message.content && <MessageContent content={message.content} />}

            {/* Render Error Alert Warning */}
            {isError && (
              <div className="flex items-center space-x-1.5 text-red-400 mt-2 pt-2 border-t border-red-500/20 text-xs font-medium">
                <AlertCircle className="w-4 h-4 text-red-500 shrink-0 inline-block" />
                <span>Failed to send or process message</span>
              </div>
            )}

            {/* Render Human Input Interrupt Tab Card */}
            {!isUser && message.humanInputRequest && (
              <InterruptTabCard
                requestData={message.humanInputRequest}
                onSubmit={handleInterruptSubmit}
                disabled={!isLatestMessage}
              />
            )}

            {/* Render Structured Data Cards */}
            {!isUser && message.structuredParts && message.structuredParts.length > 0 && (
              <div className="space-y-3">
                {message.structuredParts.map((part, idx) => {
                  if (part.kind === 'structured_data') {
                    const schemaId = String(part.schema_id || '');
                    if (schemaId === 'ecommerce.user_result.v1') {
                      return <UserInfoCard key={idx} data={part.data as ECommerceUserOutput} />;
                    } else if (schemaId === 'ecommerce.orders_result.v1') {
                      return <OrdersCard key={idx} data={part.data as ECommerceOrdersOutput} />;
                    } else if (schemaId === 'ecommerce.order_details_result.v1') {
                      return <OrderDetailsCard key={idx} data={part.data as ECommerceOrderDetailsOutput} />;
                    } else if (schemaId === 'ecommerce.returns_by_order_result.v1') {
                      return <ReturnsByOrderCard key={idx} data={part.data as ECommerceReturnsByOrderOutput} />;
                    } else if (schemaId === 'ecommerce.returns_by_customer_result.v1') {
                      return <ReturnsByCustomerCard key={idx} data={part.data as ECommerceReturnsByCustomerOutput} />;
                    } else if (schemaId === 'ecommerce.create_return_result.v1') {
                      return <CreateReturnResultCard key={idx} data={part.data as ECommerceCreateReturnOutput} />;
                    }
                  }
                  return null;
                })}
              </div>
            )}

            {/* Render Tool Calls if present */}
            {message.toolCalls && message.toolCalls.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/50 space-y-2 text-left">
                <div className="flex items-center space-x-1.5 text-xs font-semibold text-muted-foreground">
                  <Wrench className="w-3.5 h-3.5 text-amber-400" />
                  <span>Tool Execution Log</span>
                </div>
                {message.toolCalls.map((tool, idx) => (
                  <div key={idx} className="bg-muted/40 p-2.5 rounded-lg border border-border/40 text-xs font-mono">
                    <div className="flex items-center justify-between text-amber-400">
                      <span>fn: {tool.name}()</span>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <pre className="text-muted-foreground mt-1 overflow-x-auto text-[11px]">
                      args: {JSON.stringify(tool.args)}
                    </pre>
                    {tool.result && (
                      <div className="mt-1 text-emerald-300/90 text-[11px]">
                        res: {tool.result}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
