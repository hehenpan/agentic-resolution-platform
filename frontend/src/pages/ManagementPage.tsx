import React from 'react';
import { UploadCloud, Settings, Users, Database, ShieldCheck } from 'lucide-react';

export const ManagementPage: React.FC = () => {
  return (
    <div className="flex-1 h-[calc(100vh-4rem)] flex flex-col glass-panel overflow-hidden">
      {/* Management Header */}
      <div className="p-4 border-b border-border/60 flex items-center justify-between bg-muted/20">
        <div className="flex items-center space-x-2">
          <Settings className="w-5 h-5 text-indigo-400" />
          <h2 className="font-semibold text-foreground text-sm">
            Tenant Administration Console
          </h2>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
          <ShieldCheck className="w-3.5 h-3.5 mr-1" />
          <span>Admin Access Verified</span>
        </div>
      </div>

      {/* Admin Content Workspace */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Welcome Alert */}
          <div className="p-4 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 space-y-2">
            <h3 className="font-bold text-foreground text-base">Welcome to the Administration Console</h3>
            <p className="text-sm text-muted-foreground">
              Configure tenant policies, manage files index parameters, and override system configurations.
              Only authorized tenant administrators have visibility to this console.
            </p>
          </div>

          {/* Quick Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* File Upload card */}
            <div className="p-6 rounded-2xl bg-slate-900/40 border border-border/60 space-y-4 hover:border-indigo-500/40 transition-all">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <h4 className="font-bold text-sm text-foreground">File Management</h4>
              </div>
              <p className="text-xs text-muted-foreground">
                Upload knowledgebase documents (.txt, .md, .pdf) to synchronize with vector store indexes.
              </p>
              <div className="p-8 border border-dashed border-border rounded-xl flex flex-col items-center justify-center space-y-2 cursor-pointer hover:bg-slate-950/20 transition-all">
                <UploadCloud className="w-8 h-8 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">Drag files here or click to browse</span>
                <span className="text-[10px] text-slate-500">Only txt, md, and pdf are supported</span>
              </div>
            </div>

            {/* Other System Settings card */}
            <div className="p-6 rounded-2xl bg-slate-900/40 border border-border/60 space-y-4 hover:border-indigo-500/40 transition-all">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400">
                  <Users className="w-5 h-5" />
                </div>
                <h4 className="font-bold text-sm text-foreground">Tenant Resources</h4>
              </div>
              <p className="text-xs text-muted-foreground">
                Monitor system logs, vector databases, and manage tenant members.
              </p>
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between text-xs p-2 bg-slate-950/30 rounded-lg">
                  <div className="flex items-center space-x-2 text-slate-300">
                    <Database className="w-3.5 h-3.5 text-slate-500" />
                    <span>Vector DB Status</span>
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-400 font-mono">CONNECTED</span>
                </div>
                <div className="flex items-center justify-between text-xs p-2 bg-slate-950/30 rounded-lg">
                  <div className="flex items-center space-x-2 text-slate-300">
                    <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
                    <span>Active Tenant ID</span>
                  </div>
                  <span className="text-[10px] font-semibold text-indigo-400 font-mono">1</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default ManagementPage;
