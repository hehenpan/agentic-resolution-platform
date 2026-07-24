import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Header } from './Header';
import { useAuthStore } from '../../store/authStore';

/** Wrap Header with MemoryRouter since it uses useNavigate */
function renderHeader(props: { darkMode: boolean; onToggleTheme: () => void }) {
  return render(
    <MemoryRouter>
      <Header {...props} />
    </MemoryRouter>
  );
}

describe('Header Component', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: false,
      userEmail: null,
      userType: null,
    });
  });

  it('renders platform title', () => {
    renderHeader({ darkMode: true, onToggleTheme: vi.fn() });

    expect(screen.getByText('Agentic Resolution Platform')).toBeInTheDocument();
  });

  it('triggers onToggleTheme when theme button is clicked', () => {
    const handleToggle = vi.fn();
    renderHeader({ darkMode: true, onToggleTheme: handleToggle });

    const themeButton = screen.getByTitle('Toggle Theme');
    fireEvent.click(themeButton);

    expect(handleToggle).toHaveBeenCalledTimes(1);
  });

  it('shows user email and logout button when authenticated', () => {
    const logoutSpy = vi.fn();
    useAuthStore.setState({
      isAuthenticated: true,
      userEmail: 'user@example.com',
      userType: 'user',
      logout: logoutSpy,
    });

    renderHeader({ darkMode: true, onToggleTheme: vi.fn() });

    expect(screen.getByText('user@example.com')).toBeInTheDocument();
    const logoutBtn = screen.getByTitle('Sign Out');
    fireEvent.click(logoutBtn);
    expect(logoutSpy).toHaveBeenCalledTimes(1);
  });

  it('shows Admin Console button enabled for tenant_admin', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      userEmail: 'admin@tenant.com',
      userType: 'tenant_admin',
    });

    renderHeader({ darkMode: true, onToggleTheme: vi.fn() });

    const adminBtn = screen.getByText('Admin Console');
    expect(adminBtn.closest('button')).not.toBeDisabled();
  });

  it('shows Admin Console button disabled for regular user', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      userEmail: 'user@example.com',
      userType: 'user',
    });

    renderHeader({ darkMode: true, onToggleTheme: vi.fn() });

    const adminBtn = screen.getByText('Admin Console');
    expect(adminBtn.closest('button')).toBeDisabled();
  });

  it('shows Admin Console button disabled for system admin', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      userEmail: 'sysadmin@example.com',
      userType: 'admin',
    });

    renderHeader({ darkMode: true, onToggleTheme: vi.fn() });

    const adminBtn = screen.getByText('Admin Console');
    expect(adminBtn.closest('button')).toBeDisabled();
  });
});
