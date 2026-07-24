import React from 'react';
import { FileText, Calendar, DollarSign, ShoppingBag, AlertCircle } from 'lucide-react';
import type { ECommerceOrderDetailsOutput, ECommerceOrderItemOutput } from '../../types/chat';

interface OrderDetailsCardProps {
  data: ECommerceOrderDetailsOutput;
}

export const OrderDetailsCard: React.FC<OrderDetailsCardProps> = ({ data }) => {
  const getStatusBadge = (statusCode?: number) => {
    if (statusCode === undefined) return null;
    switch (statusCode) {
      case 1:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            PAID
          </span>
        );
      case 2:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
            SHIPPED
          </span>
        );
      case 3:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
            COMPLETED
          </span>
        );
      case 4:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
            CANCELLED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            PENDING
          </span>
        );
    }
  };

  if (!data.exists || !data.order) {
    return (
      <div className="mt-3 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-foreground glass-panel space-y-2 max-w-lg">
        <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>Order Not Found</span>
        </div>
        <p className="text-xs text-muted-foreground">The requested order details could not be found.</p>
      </div>
    );
  }

  const { order, items } = data;

  return (
    <div className="mt-3 p-4 rounded-2xl bg-slate-900/60 border border-slate-700/60 text-foreground glass-panel space-y-3 animate-fade-in shadow-xl shadow-slate-950/20 max-w-lg">
      {/* Card Header */}
      <div className="flex items-center justify-between border-b border-slate-700/50 pb-2.5">
        <div className="flex items-center space-x-2 text-slate-200 font-semibold text-xs uppercase tracking-wider">
          <FileText className="w-4 h-4 text-sky-400 shrink-0" />
          <span>Order Details</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="font-mono text-xs font-semibold text-sky-300">
            #{order.order_id}
          </span>
          {getStatusBadge(order.status)}
        </div>
      </div>

      {/* Order Meta Info */}
      <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-slate-800/40 border border-slate-700/30 text-xs">
        <div>
          <span className="text-muted-foreground block text-[11px]">Customer</span>
          <span className="font-mono text-foreground font-medium truncate block">{order.email}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Order Total</span>
          <span className="font-mono text-emerald-400 font-semibold flex items-center">
            <DollarSign className="w-3 h-3 inline" />
            {order.total_amount.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Created Date</span>
          <span className="text-foreground flex items-center space-x-1">
            <Calendar className="w-3 h-3 text-muted-foreground inline shrink-0" />
            <span>{new Date(order.created_ts * 1000).toLocaleDateString()}</span>
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[11px]">Customer ID</span>
          <span className="font-mono text-foreground">{order.user_id}</span>
        </div>
      </div>

      {/* Items Table */}
      <div className="space-y-2 pt-1">
        <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300">
          <ShoppingBag className="w-3.5 h-3.5 text-sky-400 shrink-0" />
          <span>Purchased Items ({items.length})</span>
        </div>

        <div className="border border-slate-700/40 rounded-xl overflow-hidden text-xs">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-800/70 border-b border-slate-700/40 text-[11px] text-muted-foreground">
                <th className="p-2 pl-3 font-medium">SKU / Item</th>
                <th className="p-2 text-center font-medium">Qty</th>
                <th className="p-2 pr-3 text-right font-medium">Price</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {items.map((item: ECommerceOrderItemOutput) => (
                <tr key={item.item_id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="p-2 pl-3">
                    <div className="font-medium text-foreground">{item.name}</div>
                    <div className="text-[10px] font-mono text-muted-foreground">{item.sku_code}</div>
                  </td>
                  <td className="p-2 text-center font-mono text-foreground font-medium">{item.quantity}</td>
                  <td className="p-2 pr-3 text-right font-mono text-emerald-400 font-medium">
                    ${item.price.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
