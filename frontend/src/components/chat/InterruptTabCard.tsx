import React, { useState } from 'react';
import { AlertCircle, Send, CheckCircle2, UserCheck, PackageSearch, FileText } from 'lucide-react';
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
  
  const [inputValue, setInputValue] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const isGetUser = schemaId.includes('get_user');
  const isGetOrders = schemaId.includes('get_orders');
  const isGetOrderDetails = schemaId.includes('get_order_details');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    setSubmitted(true);
    let payload: Record<string, unknown>;
    let displayContent: string;

    if (isGetOrderDetails) {
      const orderIdNum = parseInt(inputValue.trim(), 10);
      payload = { order_id: isNaN(orderIdNum) ? inputValue.trim() : orderIdNum };
      displayContent = `[Submitted Form] Order ID: ${inputValue.trim()}`;
    } else {
      payload = { email: inputValue.trim() };
      displayContent = `[Submitted Form] Customer Email: ${inputValue.trim()}`;
    }

    onSubmit(payload, displayContent);
  };

  const getHeaderTitle = () => {
    if (isGetUser) return 'Action Required: Customer Lookup Interrupt';
    if (isGetOrders) return 'Action Required: Customer Orders Interrupt';
    if (isGetOrderDetails) return 'Action Required: Order Details Interrupt';
    return 'Action Required: Human Input Interrupt';
  };

  return (
    <div className="mt-3 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-foreground glass-panel space-y-3 animate-fade-in shadow-lg shadow-amber-500/5">
      {/* Header */}
      <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm">
        {isGetUser ? (
          <UserCheck className="w-4 h-4 text-amber-400 shrink-0" />
        ) : isGetOrders ? (
          <PackageSearch className="w-4 h-4 text-amber-400 shrink-0" />
        ) : isGetOrderDetails ? (
          <FileText className="w-4 h-4 text-amber-400 shrink-0" />
        ) : (
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
        )}
        <span>{getHeaderTitle()}</span>
      </div>

      {/* Prompt / Instructions */}
      <p className="text-xs text-muted-foreground leading-relaxed">{prompt}</p>

      {/* Tabs / Form Section */}
      {!submitted ? (
        <form onSubmit={handleSubmit} className="space-y-3 pt-1">
          <div className="flex flex-col space-y-1.5">
            <label htmlFor="interrupt-input-field" className="text-xs font-medium text-amber-300/90">
              {isGetOrderDetails ? 'Order ID' : 'Customer Email Address'} <span className="text-rose-400">*</span>
            </label>
            <input
              id="interrupt-input-field"
              type={isGetOrderDetails ? 'number' : 'email'}
              required
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={isGetOrderDetails ? 'e.g. 88412' : 'e.g. customer@example.com'}
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
              disabled={disabled || !inputValue.trim()}
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
