import React from 'react';
import { useChatStore } from '../store/chatStore';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { ChatInputBox } from '../components/chat/ChatInputBox';
import { InterruptBanner } from '../components/chat/InterruptBanner';
import { chatService } from '../services/chatService';
import type { ChatMessage, HumanInputResponse } from '../types/chat';

export const WorkbenchPage: React.FC = () => {
  const {
    sessions,
    activeThreadId,
    isStreaming,
    activeInterrupt,
    addMessage,
    updateMessageContent,
    setMessageStatus,
    setStreaming,
    setActiveInterrupt,
  } = useChatStore();

  const currentSession = sessions.find((s) => s.threadId === activeThreadId);
  const messages = currentSession?.messages || [];

  const handleSendMessage = async (text: string) => {
    if (!activeThreadId) return;

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

    addMessage(activeThreadId, userMessage);
    addMessage(activeThreadId, assistantMessage);
    setStreaming(true);

    try {
      // Stream SSE events from FastAPI chat backend
      await chatService.streamTurn(
        {
          thread_id: activeThreadId,
          message: { content: text },
        },
        (event, data) => {
          if (event === 'token' || event === 'chunk' || event === 'message') {
            updateMessageContent(activeThreadId, assistantMessageId, data);
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
          setMessageStatus(activeThreadId, assistantMessageId, 'error');
          setStreaming(false);
        },
        () => {
          setMessageStatus(activeThreadId, assistantMessageId, 'completed');
          setStreaming(false);
        }
      );
    } catch (err) {
      console.error('Failed to trigger agent turn:', err);
      // Fallback demo response if backend is offline
      updateMessageContent(
        activeThreadId,
        assistantMessageId,
        `Agent received message: "${text}". Ready for LangGraph multi-agent execution.`
      );
      setMessageStatus(activeThreadId, assistantMessageId, 'completed');
      setStreaming(false);
    }
  };

  const handleResumeInterrupt = async (response: HumanInputResponse) => {
    if (!activeInterrupt || !activeThreadId) return;

    const resumePayload = {
      thread_id: activeThreadId,
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

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] bg-background">
      {/* Session Title Header */}
      <div className="px-6 py-3 border-b border-border/60 bg-muted/10 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-sm">{currentSession?.title || 'Resolution Workspace'}</h2>
          <p className="text-xs text-muted-foreground">Thread ID: {activeThreadId}</p>
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
            <h3 className="font-semibold text-foreground">Welcome to Agentic Resolution Platform</h3>
            <p className="text-xs max-w-md">
              Start a new session or ask a question. The LangGraph multi-agent architecture will execute tools and resolve complex tasks.
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
