import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import App from './App';
import { useAuthStore } from './store/authStore';
import { removeCookie, setCookie } from './utils/cookie';

describe('App Component', () => {
  beforeEach(() => {
    removeCookie('sessionid');
    useAuthStore.setState({
      isAuthenticated: false,
      userEmail: null,
      isLoading: false,
      error: null,
    });
  });

  it('renders login prompt modal when unauthenticated (no sessionid cookie)', () => {
    render(<App />);
    expect(screen.getByText('Agentic Platform Sign In')).toBeInTheDocument();
    expect(screen.queryByText('New Session')).not.toBeInTheDocument();
  });

  it('renders Workbench and Sidebar when authenticated (sessionid cookie present)', () => {
    setCookie('sessionid', 'valid_session_123');
    useAuthStore.setState({ isAuthenticated: true, userEmail: 'user@example.com' });

    render(<App />);
    expect(screen.queryByText('Agentic Platform Sign In')).not.toBeInTheDocument();
    expect(screen.getByText('New Session')).toBeInTheDocument();
  });
});
