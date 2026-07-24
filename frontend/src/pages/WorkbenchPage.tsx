import React from 'react';
import { MessageSquarePlus, Sparkles } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { ChatInputBox } from '../components/chat/ChatInputBox';

export const WorkbenchPage: React.FC = () => {
  const {
    sessions,
    sessionMessages,
    activeChatSessionId,
    isStreaming,
    createSession,
    fetchSessionMessages,
    sendMessageStream,
  } = useChatStore();

  const messagesEndRef = React.useRef<HTMLDivElement | null>(null);

  const currentSessionMeta = sessions.find((s) => s.chat_session_id === activeChatSessionId);
  const messages = activeChatSessionId ? sessionMessages[activeChatSessionId] || [] : [];

  const scrollToBottom = () => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  React.useEffect(() => {
    if (activeChatSessionId) {
      fetchSessionMessages(activeChatSessionId);
    }
  }, [activeChatSessionId, fetchSessionMessages]);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (text: string) => {
    if (!activeChatSessionId) return;
    await sendMessageStream(activeChatSessionId, text);
  };

  // If no chat session is selected, render empty state UI
  if (!activeChatSessionId) {
    return (
      <div className="flex-1 h-[calc(100vh-4rem)] flex flex-col items-center justify-center text-center p-8 space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
          <Sparkles className="w-8 h-8" />
        </div>
        <div className="max-w-md space-y-2">
          <h2 className="text-xl font-bold text-foreground">No Chat Session Selected</h2>
          <p className="text-sm text-muted-foreground">
            Select an existing chat session from the left sidebar or create a new session to start.
          </p>
        </div>
        <button
          onClick={() => createSession('New Chat Workspace')}
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/20"
        >
          <MessageSquarePlus className="w-4 h-4" />
          <span>Create New Session</span>
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 h-[calc(100vh-4rem)] flex flex-col glass-panel overflow-hidden">
      {/* Session Header */}
      <div className="p-4 border-b border-border/60 flex items-center justify-between bg-muted/20">
        <div>
          <h2 className="font-semibold text-foreground text-sm">
            {currentSessionMeta?.title || 'Resolution Chat Workspace'}
          </h2>
        </div>
        {isStreaming && (
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>SSE Stream Active</span>
          </div>
        )}
      </div>

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-3 text-muted-foreground my-12">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
              💬
            </div>
            <h3 className="font-semibold text-foreground">Session Ready</h3>
            <p className="text-xs max-w-md">
              Ask a question to begin. The LangGraph multi-agent architecture will execute tools and resolve your resolution workflow.
            </p>
          </div>
        ) : (
          messages.map((msg) => <ChatMessageItem key={msg.id} message={msg} />)
        )}

        {/* Scroll to bottom anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <ChatInputBox onSendMessage={handleSendMessage} disabled={isStreaming} />
    </div>
  );
};
