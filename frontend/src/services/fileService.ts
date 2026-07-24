import { request } from './httpClient';
import type { FileListResponse, FileUploadResponse } from '../types/files';

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
    return request<FileListResponse>(`/api/v1/files?${params.toString()}`, {
      method: 'GET',
    });
  },

  /**
   * Upload a file to the server via multipart/form-data.
   * Endpoint: POST /api/v1/files/upload
   */
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return request<FileUploadResponse>('/api/v1/files/upload', {
      method: 'POST',
      body: formData,
    });
  },
};
