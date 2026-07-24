import React from 'react';
import { RotateCcw, Calendar, FileCheck, HelpCircle } from 'lucide-react';
import type { ECommerceReturnsByOrderOutput } from '../../types/chat';

interface ReturnsByOrderCardProps {
  data: ECommerceReturnsByOrderOutput;
}

export const ReturnsByOrderCard: React.FC<ReturnsByOrderCardProps> = ({ data }) => {
  const getStatusBadge = (statusCode?: number) => {
    if (statusCode === undefined) return null;
    switch (statusCode) {
      case 0:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            REQUESTED
          </span>
        );
      case 1:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            APPROVED
          </span>
        );
      case 2:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
            REJECTED
          </span>
        );
      case 3:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
            RECEIVED
          </span>
        );
      case 4:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
            REFUNDED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-500/20 text-slate-300 border border-slate-500/30">
            CLOSED
          </span>
        );
    }
  };

  const getReasonLabel = (reasonCode?: number) => {
    switch (reasonCode) {
      case 0:
        return 'Change of Mind';
      case 1:
        return 'Damaged Product';
      case 2:
        return 'Wrong Item Received';
      case 3:
        return 'Not as Described';
      case 4:
        return 'Late Delivery';
      default:
        return 'Other Reason';
    }
  };

  const getConditionLabel = (conditionCode?: number) => {
    switch (conditionCode) {
      case 0:
        return 'Unopened';
      case 1:
        return 'Opened';
      case 2:
        return 'Used';
      case 3:
        return 'Damaged';
      default:
        return 'Unknown';
    }
  };

  const req = data.return_request;

  if (!req) {
    return (
      <div className="mt-3 p-4 rounded-2xl bg-slate-900/60 border border-slate-700/60 text-foreground glass-panel space-y-2 max-w-lg">
        <div className="flex items-center space-x-2 text-slate-300 font-semibold text-xs">
          <HelpCircle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>No Return Request Found</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Order <span className="font-mono font-semibold text-foreground">#{data.order_id}</span> has no associated return request history.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-3 p-4 rounded-2xl bg-slate-900/60 border border-slate-700/60 text-foreground glass-panel space-y-3 animate-fade-in shadow-xl shadow-slate-950/20 max-w-lg">
      {/* Card Header */}
      <div className="flex items-center justify-between border-b border-slate-700/50 pb-2.5">
        <div className="flex items-center space-x-2 text-slate-200 font-semibold text-xs uppercase tracking-wider">
          <RotateCcw className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Return Details for Order #{data.order_id}</span>
        </div>
        {getStatusBadge(req.status)}
      </div>

      {/* Return Request Details Grid */}
      <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-slate-800/40 border border-slate-700/30 text-xs">
        <div>
          <span className="text-muted-foreground block text-[11px]">Return Req ID</span>
          <span className="font-mono text-amber-300 font-semibold">#RET-{req.return_request_id}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Customer ID</span>
          <span className="font-mono text-foreground">{req.customer_id}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Reason</span>
          <span className="text-foreground font-medium">{getReasonLabel(req.reason_code)}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Item Condition</span>
          <span className="text-foreground font-medium">{getConditionLabel(req.item_condition)}</span>
        </div>
      </div>

      {req.reason_text && (
        <div className="p-2.5 rounded-xl bg-slate-800/20 border border-slate-700/30 text-xs space-y-1">
          <span className="text-[11px] text-muted-foreground block">Customer Explanation</span>
          <p className="text-slate-200 italic leading-relaxed">"{req.reason_text}"</p>
        </div>
      )}

      <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-slate-700/30">
        <div className="flex items-center space-x-1">
          <Calendar className="w-3 h-3 text-muted-foreground inline" />
          <span>Submitted: {new Date(req.requested_at * 1000).toLocaleDateString()}</span>
        </div>
        <div className="flex items-center space-x-1">
          <FileCheck className="w-3 h-3 text-emerald-400 inline" />
          <span>Status Code: {req.status}</span>
        </div>
      </div>
    </div>
  );
};
