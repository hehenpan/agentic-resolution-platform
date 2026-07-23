import React from 'react';
import { Bot, User, Wrench, CheckCircle2 } from 'lucide-react';
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

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message }) => {
  const { userEmail } = useAuthStore();
  const { activeChatSessionId, resumeSessionMessageStream } = useChatStore();

  const isUser = message.role === 'user';
  const userName = userEmail || 'Customer Support';

  const handleInterruptSubmit = (payload: Record<string, unknown>, displayContent?: string) => {
    if (activeChatSessionId) {
      resumeSessionMessageStream(activeChatSessionId, payload, displayContent);
    }
  };

  return (
    <div className={`flex space-x-3 max-w-4xl ${isUser ? 'ml-auto flex-row-reverse space-x-reverse' : ''}`}>
      <div
        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-md ${
          isUser
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
              <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
              <span>•</span>
              <span className="font-semibold text-foreground">{userName}</span>
            </>
          ) : (
            <>
              <span className="font-semibold text-foreground">Agent Assistant</span>
              <span>•</span>
              <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
            </>
          )}
        </div>

        <div
          className={`inline-block p-4 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-blue-600 text-white rounded-tr-none shadow-lg shadow-blue-500/10'
              : 'glass-panel text-foreground rounded-tl-none border border-border'
          }`}
        >
          {message.content && <div className="whitespace-pre-wrap">{message.content}</div>}

          {/* Render Human Input Interrupt Tab Card */}
          {!isUser && message.humanInputRequest && (
            <InterruptTabCard
              requestData={message.humanInputRequest}
              onSubmit={handleInterruptSubmit}
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
      </div>
    </div>
  );
};

