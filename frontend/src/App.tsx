import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { WorkbenchPage } from './pages/WorkbenchPage';

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

  const toggleTheme = () => {
    setDarkMode(!darkMode);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className={`min-h-screen flex flex-col ${darkMode ? 'dark' : 'light'}`}>
        <Header darkMode={darkMode} onToggleTheme={toggleTheme} />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <WorkbenchPage />
        </div>
      </div>
    </QueryClientProvider>
  );
};

export default App;
