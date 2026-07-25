import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fileService } from './fileService';
import type { FileListResponse, FileUploadResponse } from '../types/files';

describe('fileService', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uploads a file with multipart form data using the backend file field', async () => {
    const uploadResponse: FileUploadResponse = {
      code: 0,
      message: 'File uploaded successfully',
      data: {
        file_id: 100003,
        file_name: 'policy.md',
        file_size: 19,
      },
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: vi.fn().mockResolvedValue(uploadResponse),
    });
    vi.stubGlobal('fetch', fetchMock);

    const file = new File(['tenant upload body'], 'policy.md', { type: 'text/markdown' });

    const result = await fileService.uploadFile(file);

    expect(result).toEqual(uploadResponse);
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/files/upload', {
      method: 'POST',
      body: expect.any(FormData),
      headers: {
        Accept: 'application/json',
      },
    });

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = options.body as FormData;
    expect(body.get('file')).toBe(file);
  });

  it('normalizes legacy filename from file list responses to file_name', async () => {
    const listResponse = {
      code: 0,
      message: 'Success',
      data: {
        items: [
          {
            file_id: 100001,
            filename: 'legacy-name.md',
            file_name: '',
            file_size: 512,
            file_type: 'md',
            file_md5_hash: 'hash',
            owner_user_id: 101,
            owner_email: 'admin@tenant.com',
            create_ts: 1753236000,
            status: 1,
            vector_db_sync_status: 1,
          },
        ],
        last_cursor: '',
      },
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue(listResponse),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result: FileListResponse = await fileService.listFiles();

    expect(result.data.items[0].file_name).toBe('legacy-name.md');
  });

  it('normalizes legacy filename from upload responses to file_name', async () => {
    const uploadResponse = {
      code: 0,
      message: 'File uploaded successfully',
      data: {
        file_id: 100003,
        filename: 'legacy-upload.md',
        file_name: '',
        file_size: 19,
      },
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: vi.fn().mockResolvedValue(uploadResponse),
    });
    vi.stubGlobal('fetch', fetchMock);

    const file = new File(['tenant upload body'], 'legacy-upload.md', { type: 'text/markdown' });

    const result: FileUploadResponse = await fileService.uploadFile(file);

    expect(result.data.file_name).toBe('legacy-upload.md');
  });
});
