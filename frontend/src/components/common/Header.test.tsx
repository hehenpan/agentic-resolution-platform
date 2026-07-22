import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Header } from './Header';
import { useAuthStore } from '../../store/authStore';

describe('Header Component', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: false,
      userEmail: null,
    });
  });

  it('renders platform title and connection status badge', () => {
    render(<Header darkMode={true} onToggleTheme={vi.fn()} />);

    expect(screen.getByText('Agentic Resolution Platform')).toBeInTheDocument();
    expect(screen.getByText('FastAPI Connected')).toBeInTheDocument();
  });

  it('triggers onToggleTheme when theme button is clicked', () => {
    const handleToggle = vi.fn();
    render(<Header darkMode={true} onToggleTheme={handleToggle} />);

    const themeButton = screen.getByTitle('Toggle Theme');
    fireEvent.click(themeButton);

    expect(handleToggle).toHaveBeenCalledTimes(1);
  });

  it('shows user email and logout button when authenticated', () => {
    const logoutSpy = vi.fn();
    useAuthStore.setState({
      isAuthenticated: true,
      userEmail: 'user@example.com',
      logout: logoutSpy,
    });

    render(<Header darkMode={true} onToggleTheme={vi.fn()} />);

    expect(screen.getByText('user@example.com')).toBeInTheDocument();
    const logoutBtn = screen.getByTitle('Sign Out');
    fireEvent.click(logoutBtn);
    expect(logoutSpy).toHaveBeenCalledTimes(1);
  });
});
