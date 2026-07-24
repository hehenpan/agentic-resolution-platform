import React, { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { LoginModal } from './components/auth/LoginModal';
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
        
        <div className="flex-1 flex overflow-hidden relative">
          {!isAuthenticated ? (
            <LoginModal />
          ) : (
            <>
              <Sidebar />
              <WorkbenchPage />
            </>
          )}
        </div>
      </div>
    </QueryClientProvider>
  );
};

export default App;
