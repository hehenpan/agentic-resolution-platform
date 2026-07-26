import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChatMessageItem } from './ChatMessageItem';
import type { ChatMessage } from '../../types/chat';
import { useAuthStore } from '../../store/authStore';
import { fileService } from '../../services/fileService';

describe('ChatMessageItem Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders user message with logged-in user email correctly', () => {
    useAuthStore.setState({ userEmail: 'agent_user@company.com' });

    const userMsg: ChatMessage = {
      id: 'msg_1',
      role: 'user',
      content: 'Process order refund',
      timestamp: new Date().toISOString(),
    };

    render(<ChatMessageItem message={userMsg} />);
    expect(screen.getByText('agent_user@company.com')).toBeInTheDocument();
    expect(screen.getByText('Process order refund')).toBeInTheDocument();
  });

  it('renders assistant message with tool execution badges', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_2',
      role: 'assistant',
      content: 'Refund completed successfully.',
      timestamp: new Date().toISOString(),
      toolCalls: [
        {
          name: 'refund_api',
          args: { amount: 100 },
          result: 'Status 200 OK',
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);
    expect(screen.getByText('Agent Assistant')).toBeInTheDocument();
    expect(screen.getByText('Refund completed successfully.')).toBeInTheDocument();
    expect(screen.getByText('Tool Execution Log')).toBeInTheDocument();
    expect(screen.getByText('fn: refund_api()')).toBeInTheDocument();
  });

  it('renders markdown content as formatted HTML for text messages', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_3',
      role: 'assistant',
      content: '## Refund Summary\n\n- Status: **approved**\n- Amount: `$100`',
      timestamp: new Date().toISOString(),
    };

    render(<ChatMessageItem message={agentMsg} />);

    expect(screen.getByRole('heading', { name: 'Refund Summary', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('approved').tagName).toBe('STRONG');
    expect(screen.getByText('$100').tagName).toBe('CODE');
    expect(screen.queryByText('## Refund Summary')).not.toBeInTheDocument();
  });

  it('renders a spinner instead of an empty assistant message bubble while waiting for first response', () => {
    const pendingAgentMsg: ChatMessage = {
      id: 'msg_4',
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      status: 'streaming',
    };

    render(<ChatMessageItem message={pendingAgentMsg} />);

    expect(screen.getByLabelText('Waiting for assistant response')).toBeInTheDocument();
    expect(screen.getByText('Agent Assistant')).toBeInTheDocument();
    expect(screen.queryByText('Failed to send or process message')).not.toBeInTheDocument();
  });

  it('opens a preview dialog when a source reference file is clicked', async () => {
    vi.spyOn(fileService, 'downloadFileText').mockResolvedValueOnce('# Return Policy\n\nPreview content.');
    const agentMsg: ChatMessage = {
      id: 'msg_sources',
      role: 'assistant',
      content: 'Policy answer.',
      timestamp: new Date().toISOString(),
      sourceParts: [
        {
          kind: 'sources',
          sources: [
            {
              source_id: 'point_1',
              file_id: 123,
              source_type: 'policy_rag',
              title: 'returns.md',
            },
          ],
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);

    const previewButton = screen.getByTestId('source-preview-123');
    expect(screen.getByText('References')).toBeInTheDocument();
    expect(previewButton).toHaveTextContent('returns.md');

    fireEvent.click(previewButton);

    await waitFor(() => {
      expect(fileService.downloadFileText).toHaveBeenCalledWith(123);
    });
    expect(await screen.findByRole('dialog', { name: 'returns.md' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Return Policy', level: 1 })).toBeInTheDocument();
  });

  it('deduplicates source reference links by file id for display only', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_duplicate_sources',
      role: 'assistant',
      content: 'Policy answer.',
      timestamp: new Date().toISOString(),
      sourceParts: [
        {
          kind: 'sources',
          sources: [
            {
              source_id: 'point_1',
              file_id: 123,
              source_type: 'policy_rag',
              title: 'returns.md',
            },
            {
              source_id: 'point_2',
              file_id: 123,
              source_type: 'policy_rag',
              title: 'returns.md',
            },
          ],
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);

    expect(screen.getAllByTestId('source-preview-123')).toHaveLength(1);
  });

  it('deduplicates source references using payload file id fallback', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_payload_file_id_sources',
      role: 'assistant',
      content: 'Policy answer.',
      timestamp: new Date().toISOString(),
      sourceParts: [
        {
          kind: 'sources',
          sources: [
            {
              source_id: 'point_1',
              source_type: 'policy_rag',
              title: 'returns.md',
              attributes: { payload: { file_id: 456 } },
            },
            {
              source_id: 'point_2',
              source_type: 'policy_rag',
              title: 'returns.md',
              attributes: { payload: { file_id: 456 } },
            },
          ],
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);

    const previewLink = screen.getByTestId('source-preview-456');
    expect(screen.getAllByText('returns.md')).toHaveLength(1);
    expect(previewLink).toHaveTextContent('returns.md');
  });

  it('deduplicates source references by title when file id is unavailable', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_title_sources',
      role: 'assistant',
      content: 'Policy answer.',
      timestamp: new Date().toISOString(),
      sourceParts: [
        {
          kind: 'sources',
          sources: [
            {
              source_id: 'point_1',
              source_type: 'policy_rag',
              title: 'general_ecommerce_terms_and_conditions.md',
            },
            {
              source_id: 'point_2',
              source_type: 'policy_rag',
              title: 'general_ecommerce_terms_and_conditions.md',
            },
          ],
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);

    expect(screen.getAllByText('general_ecommerce_terms_and_conditions.md')).toHaveLength(1);
  });

  it('deduplicates source references by file name before file id for RAG chunks', () => {
    const agentMsg: ChatMessage = {
      id: 'msg_staging_sources',
      role: 'assistant',
      content: 'Policy answer.',
      timestamp: new Date().toISOString(),
      sourceParts: [
        {
          kind: 'sources',
          sources: [
            {
              source_id: '3170',
              file_id: 3170,
              source_type: 'policy_rag',
              title: 'general_ecommerce_terms_and_conditions.md',
            },
            {
              source_id: '5559',
              file_id: 5559,
              source_type: 'policy_rag',
              title: 'general_ecommerce_terms_and_conditions.md',
            },
            {
              source_id: '3392',
              file_id: 3392,
              source_type: 'policy_rag',
              title: 'general_ecommerce_terms_and_conditions.md',
            },
          ],
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);

    expect(screen.getAllByText('general_ecommerce_terms_and_conditions.md')).toHaveLength(1);
    expect(screen.getByTestId('source-preview-3170')).toHaveTextContent('general_ecommerce_terms_and_conditions.md');
    expect(screen.queryByTestId('source-preview-5559')).not.toBeInTheDocument();
    expect(screen.queryByTestId('source-preview-3392')).not.toBeInTheDocument();
  });

  it('shows an error in the source preview dialog when preview loading fails', async () => {
    vi.spyOn(fileService, 'downloadFileText').mockRejectedValueOnce(new Error('Preview failed'));
    const agentMsg: ChatMessage = {
      id: 'msg_source_error',
      role: 'assistant',
      content: 'Policy answer.',
      timestamp: new Date().toISOString(),
      sourceParts: [
        {
          kind: 'sources',
          sources: [
            {
              source_id: 'point_1',
              file_id: 999,
              source_type: 'policy_rag',
              title: 'returns.txt',
            },
          ],
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);

    fireEvent.click(screen.getByTestId('source-preview-999'));

    expect(await screen.findByRole('dialog', { name: 'returns.txt' })).toBeInTheDocument();
    expect(await screen.findByText('Preview failed')).toBeInTheDocument();
  });

  it('closes the source preview dialog when Escape is pressed', async () => {
    vi.spyOn(fileService, 'downloadFileText').mockResolvedValueOnce('Preview content.');
    const agentMsg: ChatMessage = {
      id: 'msg_source_escape',
      role: 'assistant',
      content: 'Policy answer.',
      timestamp: new Date().toISOString(),
      sourceParts: [
        {
          kind: 'sources',
          sources: [
            {
              source_id: 'point_1',
              file_id: 321,
              source_type: 'policy_rag',
              title: 'returns.txt',
            },
          ],
        },
      ],
    };

    render(<ChatMessageItem message={agentMsg} />);

    fireEvent.click(screen.getByTestId('source-preview-321'));
    expect(await screen.findByRole('dialog', { name: 'returns.txt' })).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'returns.txt' })).not.toBeInTheDocument();
    });
  });
});
