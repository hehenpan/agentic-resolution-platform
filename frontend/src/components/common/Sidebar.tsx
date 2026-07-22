import React, { useEffect } from 'react';
import { Plus, MessageSquare, Shield, Terminal, Loader2 } from 'lucide-react';
import { useChatStore } from '../../store/chatStore';

export const Sidebar: React.FC = () => {
  const {
    sessions,
    activeChatSessionId,
    isLoadingSessions,
    fetchSessions,
    createSession,
    setActiveChatSession,
  } = useChatStore();

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleCreateNewSession = async () => {
    await createSession('New Chat Session');
  };

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return 'Recent';
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <aside className="w-72 border-r border-border bg-card/60 flex flex-col h-[calc(100vh-4rem)]">
      <div className="p-4 border-b border-border">
        <button
          onClick={handleCreateNewSession}
          className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-primary text-primary-foreground font-medium hover:opacity-90 transition-all shadow-md shadow-blue-500/20"
        >
          <Plus className="w-4 h-4" />
          <span>New Session</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
          <span>Active Sessions</span>
          {isLoadingSessions && <Loader2 className="w-3 h-3 animate-spin text-primary" />}
        </div>

        {sessions.length === 0 && !isLoadingSessions && (
          <div className="p-4 text-center text-xs text-muted-foreground">
            No sessions available. Click "New Session" to create one.
          </div>
        )}

        {sessions.map((session) => {
          const isActive = session.chat_session_id === activeChatSessionId;
          return (
            <button
              key={session.chat_session_id}
              onClick={() => setActiveChatSession(session.chat_session_id)}
              className={`w-full text-left p-3 rounded-xl transition-all flex items-start space-x-3 group ${
                isActive
                  ? 'bg-primary/10 border border-primary/20 text-foreground'
                  : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
              }`}
            >
              <MessageSquare className={`w-4 h-4 mt-0.5 shrink-0 ${isActive ? 'text-primary' : ''}`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{session.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5 truncate">
                  {formatDate(session.update_ts)}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      <div className="p-4 border-t border-border bg-muted/20 space-y-2">
        <div className="flex items-center space-x-2 text-xs text-muted-foreground">
          <Shield className="w-4 h-4 text-primary" />
          <span>LangGraph Supervisor Subgraphs</span>
        </div>
        <div className="flex items-center space-x-2 text-xs text-muted-foreground">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span>Human-in-the-Loop Interrupts</span>
        </div>
      </div>
    </aside>
  );
};
