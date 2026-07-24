import React from 'react';
import { Bot, Moon, Sun, LogOut, User, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

interface HeaderProps {
  darkMode: boolean;
  onToggleTheme: () => void;
}

export const Header: React.FC<HeaderProps> = ({ darkMode, onToggleTheme }) => {
  const { isAuthenticated, userEmail, userType, logout } = useAuthStore();
  const navigate = useNavigate();

  const isTenantAdmin = userType === 'tenant_admin';

  return (
    <header className="h-16 border-b border-border glass-panel px-6 flex items-center justify-between z-10">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-semibold text-lg tracking-tight">Agentic Resolution Platform</h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
              v1.0
            </span>
          </div>
          <p className="text-xs text-muted-foreground">LangGraph & MCP Multi-Agent Orchestrator & Resolution Workbench</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {isAuthenticated && (
          <div className="flex items-center space-x-3 border-l border-border pl-4">
            <div className="flex items-center space-x-2 text-xs text-slate-300 bg-slate-800/60 px-2.5 py-1.5 rounded-lg border border-slate-700/50">
              <User className="w-3.5 h-3.5 text-blue-400" />
              <span>{userEmail || 'Authenticated User'}</span>
            </div>
            <button
              id="admin-console-button"
              onClick={() => navigate('/tenant_admin')}
              disabled={!isTenantAdmin}
              className={`flex items-center space-x-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors ${
                isTenantAdmin
                  ? 'text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 border-indigo-500/20 cursor-pointer'
                  : 'text-slate-500 bg-slate-800/30 border-slate-700/30 cursor-not-allowed opacity-50'
              }`}
              title={isTenantAdmin ? 'Open Admin Console' : 'Admin access restricted to Tenant Admins'}
            >
              <Settings className="w-3.5 h-3.5" />
              <span>Admin Console</span>
            </button>
            <button
              onClick={() => logout()}
              className="flex items-center space-x-1.5 text-xs text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 px-2.5 py-1.5 rounded-lg border border-rose-500/20 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
          </div>
        )}

        <button
          onClick={onToggleTheme}
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          title="Toggle Theme"
        >
          {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
      </div>
    </header>
  );
};
