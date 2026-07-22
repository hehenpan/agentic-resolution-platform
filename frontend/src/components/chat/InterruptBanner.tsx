import React, { useState } from 'react';
import { AlertTriangle, Check, X } from 'lucide-react';
import type { InterruptEventData, HumanInputResponse } from '../../types/chat';

interface InterruptBannerProps {
  interrupt: InterruptEventData;
  onResume: (response: HumanInputResponse) => void;
}

export const InterruptBanner: React.FC<InterruptBannerProps> = ({ interrupt, onResume }) => {
  const [feedback, setFeedback] = useState('');

  const handleAction = (action: 'approve' | 'reject' | 'submit') => {
    onResume({
      action,
      feedback: feedback.trim() || undefined,
    });
  };

  return (
    <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 space-y-3 glass-panel animate-fade-in my-4">
      <div className="flex items-center space-x-2 font-semibold text-sm">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
        <span>Human-in-the-Loop Approval Required (Node: {interrupt.node_name})</span>
      </div>

      <p className="text-xs text-amber-300/80">
        {interrupt.description || 'The agent graph hit an interrupt checkpoint and is awaiting human input before continuing execution.'}
      </p>

      <div className="flex flex-col sm:flex-row items-center gap-2 pt-2">
        <input
          type="text"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Optional feedback / instructions for resume..."
          className="flex-1 w-full bg-background/80 border border-amber-500/30 rounded-xl px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-amber-400"
        />

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={() => handleAction('approve')}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Approve</span>
          </button>

          <button
            onClick={() => handleAction('reject')}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            <span>Reject</span>
          </button>
        </div>
      </div>
    </div>
  );
};
