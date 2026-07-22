import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Header } from './Header';

describe('Header Component', () => {
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
});
