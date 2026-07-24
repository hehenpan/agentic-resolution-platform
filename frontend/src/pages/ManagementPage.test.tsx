import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ManagementPage } from './ManagementPage';
import * as fileServiceModule from '../services/fileService';
import type { FileListResponse, FileUploadResponse } from '../types/files';

// Mock the fileService module
vi.mock('../services/fileService', () => ({
  fileService: {
    listFiles: vi.fn(),
    uploadFile: vi.fn(),
  },
}));

const mockListFiles = vi.mocked(fileServiceModule.fileService.listFiles);
const mockUploadFile = vi.mocked(fileServiceModule.fileService.uploadFile);

const mockFileListResponse: FileListResponse = {
  code: 0,
  message: 'Success',
  data: {
    items: [
      {
        file_id: 100001,
        file_name: 'policy_doc.pdf',
        file_size: 204800,
        file_type: 'pdf',
        file_md5_hash: 'abc123',
        owner_user_id: 101,
        owner_email: 'admin@tenant.com',
        create_ts: 1753236000,
        status: 1,
        vector_db_sync_status: 1,
      },
      {
        file_id: 100002,
        file_name: 'readme.md',
        file_size: 1024,
        file_type: 'md',
        file_md5_hash: 'def456',
        owner_user_id: 101,
        owner_email: 'admin@tenant.com',
        create_ts: 1753236100,
        status: 1,
        vector_db_sync_status: 0,
      },
    ],
    last_cursor: '',
  },
};

const mockEmptyListResponse: FileListResponse = {
  code: 0,
  message: 'Success',
  data: {
    items: [],
    last_cursor: '',
  },
};

const mockUploadResponse: FileUploadResponse = {
  code: 0,
  message: 'File uploaded successfully',
  data: {
    file_id: 100003,
    file_name: 'new_file.txt',
    file_size: 512,
  },
};

describe('ManagementPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state then file list after fetch', async () => {
    mockListFiles.mockResolvedValueOnce(mockFileListResponse);

    render(<ManagementPage />);

    // Initially shows loading
    expect(screen.getByText('Loading files...')).toBeInTheDocument();

    // After fetch completes, shows file names
    await waitFor(() => {
      expect(screen.getByText('policy_doc.pdf')).toBeInTheDocument();
      expect(screen.getByText('readme.md')).toBeInTheDocument();
    });
  });

  it('renders empty state when no files are present', async () => {
    mockListFiles.mockResolvedValueOnce(mockEmptyListResponse);

    render(<ManagementPage />);

    await waitFor(() => {
      expect(screen.getByText('No files uploaded yet')).toBeInTheDocument();
    });
  });

  it('renders upload file button', async () => {
    mockListFiles.mockResolvedValueOnce(mockFileListResponse);

    render(<ManagementPage />);

    await waitFor(() => {
      expect(screen.getByText('Upload File')).toBeInTheDocument();
    });
  });

  it('triggers file upload when file is selected', async () => {
    mockListFiles.mockResolvedValue(mockFileListResponse);
    mockUploadFile.mockResolvedValueOnce(mockUploadResponse);

    render(<ManagementPage />);

    await waitFor(() => {
      expect(screen.getByText('policy_doc.pdf')).toBeInTheDocument();
    });

    // Simulate file selection
    const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
    const testFile = new File(['test content'], 'new_file.txt', { type: 'text/plain' });

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(mockUploadFile).toHaveBeenCalledWith(testFile);
    });
  });

  it('renders delete buttons for each file row', async () => {
    mockListFiles.mockResolvedValueOnce(mockFileListResponse);

    render(<ManagementPage />);

    await waitFor(() => {
      expect(screen.getByTestId('delete-file-100001')).toBeInTheDocument();
      expect(screen.getByTestId('delete-file-100002')).toBeInTheDocument();
    });
  });

  it('hides file row when delete button is clicked', async () => {
    mockListFiles.mockResolvedValueOnce(mockFileListResponse);

    render(<ManagementPage />);

    await waitFor(() => {
      expect(screen.getByText('policy_doc.pdf')).toBeInTheDocument();
    });

    // Click the delete button for the first file
    fireEvent.click(screen.getByTestId('delete-file-100001'));

    // The file should be hidden from the list
    await waitFor(() => {
      expect(screen.queryByText('policy_doc.pdf')).not.toBeInTheDocument();
      // The other file should still be visible
      expect(screen.getByText('readme.md')).toBeInTheDocument();
    });
  });

  it('renders sync status badges correctly', async () => {
    mockListFiles.mockResolvedValueOnce(mockFileListResponse);

    render(<ManagementPage />);

    await waitFor(() => {
      // First file has sync status 1 (Synced), second has 0 (Pending)
      expect(screen.getByText('Synced')).toBeInTheDocument();
      expect(screen.getByText('Pending')).toBeInTheDocument();
    });
  });

  it('shows success toast after upload', async () => {
    mockListFiles.mockResolvedValue(mockFileListResponse);
    mockUploadFile.mockResolvedValueOnce(mockUploadResponse);

    render(<ManagementPage />);

    await waitFor(() => {
      expect(screen.getByText('policy_doc.pdf')).toBeInTheDocument();
    });

    const fileInput = screen.getByTestId('file-input') as HTMLInputElement;
    const testFile = new File(['test content'], 'new_file.txt', { type: 'text/plain' });
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(screen.getByText('File "new_file.txt" uploaded successfully.')).toBeInTheDocument();
    });
  });
});
