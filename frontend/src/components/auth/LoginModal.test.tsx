import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { LoginModal } from './LoginModal';
import { useAuthStore } from '../../store/authStore';

describe('LoginModal Component', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: false,
      userEmail: null,
      isLoading: false,
      error: null,
    });
  });

  it('renders login prompt title and inputs', () => {
    render(<LoginModal />);

    expect(screen.getByText('Agentic Platform Sign In')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('user@example.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
  });

  it('shows validation error when fields are empty', async () => {
    render(<LoginModal />);

    const submitBtn = screen.getByRole('button', { name: /Sign In/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText('Please enter username or email')).toBeInTheDocument();
  });

  it('calls login when valid inputs are submitted', async () => {
    const loginSpy = vi.fn().mockResolvedValue(true);
    useAuthStore.setState({ login: loginSpy });

    render(<LoginModal />);

    const emailInput = screen.getByPlaceholderText('user@example.com');
    const passwordInput = screen.getByPlaceholderText('••••••••');
    const submitBtn = screen.getByRole('button', { name: /Sign In/i });

    fireEvent.change(emailInput, { target: { value: 'admin@test.com' } });
    fireEvent.change(passwordInput, { target: { value: '123456' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith({
        email: 'admin@test.com',
        password: '123456',
      });
    });
  });
});
