import { request } from './httpClient';
import type { FileItemResponse, FileListResponse, FileUploadResponse } from '../types/files';

type RawFileItemResponse = FileItemResponse & {
  filename?: string;
};

type RawFileUploadResponse = FileUploadResponse & {
  data: FileUploadResponse['data'] & {
    filename?: string;
  };
};

function normalizeFileItem(item: RawFileItemResponse): FileItemResponse {
  return {
    ...item,
    file_name: item.file_name || item.filename || '',
  };
}

function normalizeFileListResponse(response: FileListResponse): FileListResponse {
  return {
    ...response,
    data: {
      ...response.data,
      items: response.data.items.map((item) => normalizeFileItem(item)),
    },
  };
}

function normalizeFileUploadResponse(response: RawFileUploadResponse): FileUploadResponse {
  return {
    ...response,
    data: {
      ...response.data,
      file_name: response.data.file_name || response.data.filename || '',
    },
  };
}

export const fileService = {
  /**
   * List files belonging to the current tenant with cursor pagination.
   * Endpoint: GET /api/v1/files
   */
  async listFiles(cursor?: string, limit = 20): Promise<FileListResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (cursor) {
      params.append('cursor', cursor);
    }
    const response = await request<FileListResponse>(`/api/v1/files?${params.toString()}`, {
      method: 'GET',
    });
    return normalizeFileListResponse(response);
  },

  /**
   * Upload a file to the server via multipart/form-data.
   * Endpoint: POST /api/v1/files/upload
   */
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await request<RawFileUploadResponse>('/api/v1/files/upload', {
      method: 'POST',
      body: formData,
    });
    return normalizeFileUploadResponse(response);
  },

  /**
   * Download a file as text for in-browser preview.
   * Endpoint: GET /api/v1/files/{file_id}
   */
  async downloadFileText(fileId: number): Promise<string> {
    const response = await fetch(`/api/v1/files/${fileId}`, {
      method: 'GET',
      headers: {
        Accept: 'text/plain, text/markdown, application/octet-stream',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to download file with status ${response.status}`);
    }

    return response.text();
  },
};
