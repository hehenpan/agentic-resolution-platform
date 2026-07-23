import React from 'react';
import { Package, Calendar, DollarSign, Tag } from 'lucide-react';
import type { ECommerceOrdersOutput, ECommerceOrderOutput } from '../../types/chat';

interface OrdersCardProps {
  data: ECommerceOrdersOutput;
}

export const OrdersCard: React.FC<OrdersCardProps> = ({ data }) => {
  const getStatusBadge = (statusCode: number) => {
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

  return (
    <div className="mt-3 p-4 rounded-2xl bg-slate-900/60 border border-slate-700/60 text-foreground glass-panel space-y-3 animate-fade-in shadow-xl shadow-slate-950/20 max-w-lg">
      {/* Card Header */}
      <div className="flex items-center justify-between border-b border-slate-700/50 pb-2.5">
        <div className="flex items-center space-x-2 text-slate-200 font-semibold text-xs uppercase tracking-wider">
          <Package className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Customer Order History</span>
        </div>
        <span className="text-[11px] text-muted-foreground font-mono">
          {data.orders.length} order{data.orders.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="text-xs text-muted-foreground font-mono">
        Customer: <span className="text-foreground">{data.customer_email}</span>
      </div>

      {/* Orders List / Table */}
      <div className="space-y-2 pt-1">
        {data.orders.map((order: ECommerceOrderOutput) => (
          <div
            key={order.order_id}
            className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/40 hover:border-emerald-500/30 transition-all space-y-2"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Tag className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="font-mono text-xs font-semibold text-emerald-300">
                  Order #{order.order_id}
                </span>
              </div>
              {getStatusBadge(order.status)}
            </div>

            <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t border-slate-700/30">
              <div className="flex items-center space-x-1">
                <Calendar className="w-3 h-3 text-muted-foreground/70" />
                <span>{new Date(order.created_ts * 1000).toLocaleDateString()}</span>
              </div>

              <div className="flex items-center space-x-0.5 font-mono text-foreground font-medium">
                <DollarSign className="w-3 h-3 text-emerald-400" />
                <span>{order.total_amount.toFixed(2)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
