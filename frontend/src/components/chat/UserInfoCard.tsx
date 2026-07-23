import React from 'react';
import { User, CheckCircle2, XCircle, Mail, ShieldCheck } from 'lucide-react';
import type { ECommerceUserOutput } from '../../types/chat';

interface UserInfoCardProps {
  data: ECommerceUserOutput;
}

export const UserInfoCard: React.FC<UserInfoCardProps> = ({ data }) => {
  return (
    <div className="mt-3 p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/30 text-foreground glass-panel space-y-3 animate-fade-in shadow-xl shadow-indigo-500/5 max-w-md">
      {/* Card Header */}
      <div className="flex items-center justify-between border-b border-indigo-500/20 pb-2.5">
        <div className="flex items-center space-x-2 text-indigo-300 font-semibold text-xs uppercase tracking-wider">
          <User className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>E-Commerce User Profile</span>
        </div>
        {data.exists ? (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            <span>Found</span>
          </span>
        ) : (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30">
            <XCircle className="w-3 h-3" />
            <span>Not Found</span>
          </span>
        )}
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground text-[11px] block mb-0.5">User ID</span>
          <span className="font-mono text-indigo-200 font-medium">
            {data.user_id ? `#${data.user_id}` : 'N/A'}
          </span>
        </div>

        <div>
          <span className="text-muted-foreground text-[11px] block mb-0.5">Username</span>
          <span className="text-foreground font-medium flex items-center space-x-1">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span>{data.user_name || 'Customer'}</span>
          </span>
        </div>

        <div className="col-span-2">
          <span className="text-muted-foreground text-[11px] block mb-0.5">Email Address</span>
          <span className="text-foreground font-medium flex items-center space-x-1 font-mono text-xs">
            <Mail className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span>{data.email}</span>
          </span>
        </div>
      </div>
    </div>
  );
};
