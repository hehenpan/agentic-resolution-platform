import React, { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { ManagementPage } from './pages/ManagementPage';
import { LoginModal } from './components/auth/LoginModal';
import { ProtectedRoute, AdminRoute } from './components/auth/RouteGuards';
import { useAuthStore } from './store/authStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  const [darkMode, setDarkMode] = useState(true);
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
  }, [darkMode]);

  const toggleTheme = () => {
    setDarkMode(!darkMode);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className={`h-screen max-h-screen flex flex-col overflow-hidden ${darkMode ? 'dark' : 'light'}`}>
        <Header darkMode={darkMode} onToggleTheme={toggleTheme} />
        
        <Routes>
          <Route
            path="/"
            element={
              !isAuthenticated ? (
                <div className="flex-1 flex overflow-hidden relative">
                  <LoginModal />
                </div>
              ) : (
                <Navigate to="/chat" replace />
              )
            }
          />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <div className="flex-1 flex overflow-hidden relative">
                  <Sidebar />
                  <WorkbenchPage />
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/tenant_admin"
            element={
              <AdminRoute>
                <div className="flex-1 flex overflow-hidden relative">
                  <Sidebar />
                  <ManagementPage />
                </div>
              </AdminRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </QueryClientProvider>
  );
};

export default App;
