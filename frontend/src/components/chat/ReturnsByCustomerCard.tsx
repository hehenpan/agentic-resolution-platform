import React from 'react';
import { RotateCcw, Calendar, FileQuestion, Tag } from 'lucide-react';
import type { ECommerceReturnsByCustomerOutput } from '../../types/chat';

interface ReturnsByCustomerCardProps {
  data: ECommerceReturnsByCustomerOutput;
}

export const ReturnsByCustomerCard: React.FC<ReturnsByCustomerCardProps> = ({ data }) => {
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

  const returns = data.returns || [];

  // Requirement 1: Empty State UI Representation
  if (returns.length === 0) {
    return (
      <div className="mt-3 p-4 rounded-2xl bg-amber-500/5 border border-amber-500/20 text-foreground glass-panel space-y-2 max-w-lg animate-fade-in">
        <div className="flex items-center space-x-2 text-amber-400 font-semibold text-xs">
          <FileQuestion className="w-4 h-4 text-amber-400 shrink-0" />
          <span>No Return History Found</span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Customer <span className="font-mono font-semibold text-slate-200">#{data.customer_id}</span> has no associated return requests in the system.
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
          <span>Customer Return History ({returns.length})</span>
        </div>
        <span className="text-xs font-mono text-amber-300 font-semibold">
          Customer #{data.customer_id}
        </span>
      </div>

      {/* Return Requests List */}
      <div className="space-y-3">
        {returns.map((req, idx) => (
          <div
            key={idx}
            className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/40 text-xs space-y-2 hover:border-slate-600/60 transition-all"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-amber-300 font-bold">#RET-{req.return_request_id}</span>
              {getStatusBadge(req.status)}
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs pt-1">
              <div>
                <span className="text-muted-foreground block text-[11px]">Order ID</span>
                <span className="font-mono text-foreground font-semibold flex items-center space-x-1">
                  <Tag className="w-3 h-3 text-slate-400 inline" />
                  <span>#{req.order_id}</span>
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Reason</span>
                <span className="text-foreground font-medium">{getReasonLabel(req.reason_code)}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Item Condition</span>
                <span className="text-foreground font-medium">{getConditionLabel(req.item_condition)}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Submitted Date</span>
                <span className="text-foreground flex items-center space-x-1">
                  <Calendar className="w-3 h-3 text-muted-foreground inline shrink-0" />
                  <span>{new Date((req.created_at || req.requested_at) * 1000).toLocaleDateString()}</span>
                </span>
              </div>
            </div>

            {req.reason_text && (
              <div className="pt-1 text-[11px] text-slate-300 italic border-t border-slate-700/30">
                "{req.reason_text}"
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
