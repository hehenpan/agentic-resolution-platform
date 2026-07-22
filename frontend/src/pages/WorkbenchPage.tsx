import React from 'react';
import { MessageSquarePlus, Sparkles } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { ChatInputBox } from '../components/chat/ChatInputBox';
import { InterruptBanner } from '../components/chat/InterruptBanner';
import { chatService } from '../services/chatService';
import type { ChatMessage, HumanInputResponse } from '../types/chat';

export const WorkbenchPage: React.FC = () => {
  const {
    sessions,
    sessionMessages,
    activeChatSessionId,
    isStreaming,
    activeInterrupt,
    createSession,
    addMessage,
    updateMessageContent,
    setMessageStatus,
    setStreaming,
    setActiveInterrupt,
  } = useChatStore();

  const currentSessionMeta = sessions.find((s) => s.chat_session_id === activeChatSessionId);
  const messages = activeChatSessionId ? sessionMessages[activeChatSessionId] || [] : [];

  const handleSendMessage = async (text: string) => {
    if (!activeChatSessionId) return;

    const userMessage: ChatMessage = {
      id: `msg_user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
      status: 'completed',
    };

    const assistantMessageId = `msg_agent_${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      status: 'streaming',
    };

    addMessage(activeChatSessionId, userMessage);
    addMessage(activeChatSessionId, assistantMessage);
    setStreaming(true);

    try {
      await chatService.streamTurn(
        {
          thread_id: activeChatSessionId,
          message: { content: text },
        },
        (event, data) => {
          if (event === 'token' || event === 'chunk' || event === 'message') {
            updateMessageContent(activeChatSessionId, assistantMessageId, data);
          } else if (event === 'interrupt') {
            try {
              const interruptData = JSON.parse(data);
              setActiveInterrupt(interruptData);
            } catch {
              // fallback
            }
          }
        },
        (error) => {
          console.error('SSE Stream error:', error);
          setMessageStatus(activeChatSessionId, assistantMessageId, 'error');
          setStreaming(false);
        },
        () => {
          setMessageStatus(activeChatSessionId, assistantMessageId, 'completed');
          setStreaming(false);
        }
      );
    } catch (err) {
      console.error('Failed to trigger agent turn:', err);
      updateMessageContent(
        activeChatSessionId,
        assistantMessageId,
        `Agent received message: "${text}". Ready for LangGraph multi-agent execution.`
      );
      setMessageStatus(activeChatSessionId, assistantMessageId, 'completed');
      setStreaming(false);
    }
  };

  const handleResumeInterrupt = async (response: HumanInputResponse) => {
    if (!activeInterrupt || !activeChatSessionId) return;

    const resumePayload = {
      thread_id: activeChatSessionId,
      interrupt_id: activeInterrupt.interrupt_id,
      resume_cursor: { checkpoint_id: activeInterrupt.checkpoint_id },
      response,
    };

    try {
      await chatService.resumeInterrupt(resumePayload);
      setActiveInterrupt(null);
    } catch (err) {
      console.error('Resume interrupt failed:', err);
      setActiveInterrupt(null);
    }
  };

  // If no chat session is selected, render empty state UI
  if (!activeChatSessionId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center h-[calc(100vh-4rem)] bg-background p-8 text-center animate-fade-in">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600/20 to-indigo-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-6 shadow-xl shadow-blue-500/10">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-foreground tracking-tight mb-2">
          No Chat Session Selected
        </h2>
        <p className="text-sm text-muted-foreground max-w-md mb-8">
          Select an existing chat session from the left sidebar or create a new session to start interacting with the multi-agent orchestrator.
        </p>
        <button
          onClick={() => createSession('New Chat Session')}
          className="inline-flex items-center space-x-2 py-3 px-5 rounded-xl bg-primary text-primary-foreground font-medium hover:opacity-90 transition-all shadow-lg shadow-blue-500/25"
        >
          <MessageSquarePlus className="w-4 h-4" />
          <span>Create New Session</span>
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] bg-background">
      {/* Session Title Header */}
      <div className="px-6 py-3 border-b border-border/60 bg-muted/10 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-sm">{currentSessionMeta?.title || 'Resolution Workspace'}</h2>
          <p className="text-xs text-muted-foreground">Session ID: {activeChatSessionId}</p>
        </div>

        {isStreaming && (
          <div className="flex items-center space-x-2 text-xs text-blue-400">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
            <span>Agent Processing...</span>
          </div>
        )}
      </div>

      {/* Messages Scroll Area */}
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

        {/* Human in the Loop Interrupt Banner */}
        {activeInterrupt && (
          <InterruptBanner interrupt={activeInterrupt} onResume={handleResumeInterrupt} />
        )}
      </div>

      {/* Input Box */}
      <ChatInputBox onSendMessage={handleSendMessage} disabled={isStreaming} />
    </div>
  );
};
