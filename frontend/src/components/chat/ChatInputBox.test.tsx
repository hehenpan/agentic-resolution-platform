import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ChatInputBox } from './ChatInputBox';

describe('ChatInputBox Component', () => {
  it('disables the send button while waiting for an assistant response', () => {
    const onSendMessage = vi.fn();

    render(<ChatInputBox onSendMessage={onSendMessage} disabled />);

    const textarea = screen.getByPlaceholderText('Ask agentic-resolution-platform or submit task...');
    fireEvent.change(textarea, { target: { value: 'Check refund status' } });

    const sendButton = screen.getByRole('button', { name: 'Send message' });
    expect(sendButton).toBeDisabled();

    fireEvent.click(sendButton);
    expect(onSendMessage).not.toHaveBeenCalled();
  });
});
