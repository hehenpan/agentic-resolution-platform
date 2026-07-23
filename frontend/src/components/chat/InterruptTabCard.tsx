import React, { useState } from 'react';
import { AlertCircle, Send, CheckCircle2, UserCheck, PackageSearch } from 'lucide-react';
import type { WebHumanInputRequestedData } from '../../types/chat';

interface InterruptTabCardProps {
  requestData: WebHumanInputRequestedData;
  onSubmit: (payload: Record<string, unknown>, displayContent?: string) => void;
  disabled?: boolean;
}

export const InterruptTabCard: React.FC<InterruptTabCardProps> = ({
  requestData,
  onSubmit,
  disabled = false,
}) => {
  const schemaId = requestData?.request?.schema_id || '';
  const prompt = requestData?.request?.prompt || 'Human-in-the-Loop input required.';
  
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const isGetUser = schemaId.includes('get_user');
  const isGetOrders = schemaId.includes('get_orders');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setSubmitted(true);
    const payload = { email: email.trim() };
    const displayContent = `[Submitted Form] Customer Email: ${email.trim()}`;
    onSubmit(payload, displayContent);
  };

  return (
    <div className="mt-3 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-foreground glass-panel space-y-3 animate-fade-in shadow-lg shadow-amber-500/5">
      {/* Header */}
      <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm">
        {isGetUser ? (
          <UserCheck className="w-4 h-4 text-amber-400 shrink-0" />
        ) : isGetOrders ? (
          <PackageSearch className="w-4 h-4 text-amber-400 shrink-0" />
        ) : (
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
        )}
        <span>Action Required: Customer Lookup Interrupt</span>
      </div>

      {/* Prompt / Instructions */}
      <p className="text-xs text-muted-foreground leading-relaxed">{prompt}</p>

      {/* Tabs / Form Section */}
      {!submitted ? (
        <form onSubmit={handleSubmit} className="space-y-3 pt-1">
          <div className="flex flex-col space-y-1.5">
            <label htmlFor="customer-email-input" className="text-xs font-medium text-amber-300/90">
              Customer Email Address <span className="text-rose-400">*</span>
            </label>
            <input
              id="customer-email-input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. customer@example.com"
              disabled={disabled}
              className="w-full px-3.5 py-2.5 text-xs bg-slate-900 border border-amber-500/40 rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all font-medium shadow-inner"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-muted-foreground/80 italic">
              Tip: You can submit via this tab form or type in the chat box.
            </span>

            <button
              type="submit"
              disabled={disabled || !email.trim()}
              className="inline-flex items-center space-x-1.5 px-4 py-1.5 bg-amber-500 hover:bg-amber-600 active:scale-95 disabled:opacity-50 text-slate-950 font-semibold text-xs rounded-xl shadow-md transition-all shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Commit Input</span>
            </button>
          </div>
        </form>
      ) : (
        <div className="flex items-center space-x-2 text-emerald-400 text-xs py-1">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>Input committed successfully. Resuming Agent execution...</span>
        </div>
      )}
    </div>
  );
};
