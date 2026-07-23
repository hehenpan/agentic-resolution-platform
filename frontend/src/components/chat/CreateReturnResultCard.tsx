import React from 'react';
import { CheckCircle2, AlertCircle, Calendar, PlusCircle, Tag } from 'lucide-react';
import type { ECommerceCreateReturnOutput } from '../../types/chat';

interface CreateReturnResultCardProps {
  data: ECommerceCreateReturnOutput;
}

export const CreateReturnResultCard: React.FC<CreateReturnResultCardProps> = ({ data }) => {
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

  if (!data.success || !data.return_request) {
    return (
      <div className="mt-3 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-foreground glass-panel space-y-2 max-w-lg">
        <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>Return Request Creation Failed</span>
        </div>
        <p className="text-xs text-muted-foreground">{data.error_message || 'Failed to create return request.'}</p>
      </div>
    );
  }

  const req = data.return_request;

  return (
    <div className="mt-3 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-foreground glass-panel space-y-3 animate-fade-in shadow-xl shadow-emerald-950/10 max-w-lg">
      {/* Card Header */}
      <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2.5">
        <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-xs uppercase tracking-wider">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Return Request Created Successfully</span>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          REQUESTED
        </span>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-slate-900/60 border border-slate-700/40 text-xs">
        <div>
          <span className="text-muted-foreground block text-[11px]">Return Req ID</span>
          <span className="font-mono text-emerald-300 font-bold text-sm">#RET-{req.return_request_id}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Order ID</span>
          <span className="font-mono text-foreground font-semibold flex items-center space-x-1">
            <Tag className="w-3 h-3 text-slate-400 inline" />
            <span>#{req.order_id}</span>
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Customer ID</span>
          <span className="font-mono text-foreground">{req.customer_id}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Reason</span>
          <span className="text-amber-300 font-medium">{getReasonLabel(req.reason_code)}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Item Condition</span>
          <span className="text-foreground font-medium">{getConditionLabel(req.item_condition)}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Submitted Date</span>
          <span className="text-foreground flex items-center space-x-1">
            <Calendar className="w-3 h-3 text-muted-foreground inline shrink-0" />
            <span>{new Date(req.created_at * 1000).toLocaleDateString()}</span>
          </span>
        </div>
      </div>

      {req.reason_text && (
        <div className="p-2.5 rounded-xl bg-slate-900/50 border border-slate-700/40 text-xs space-y-1">
          <span className="text-[11px] text-muted-foreground block">Explanation</span>
          <p className="text-slate-200 italic">"{req.reason_text}"</p>
        </div>
      )}
    </div>
  );
};
