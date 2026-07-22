/** Centralized HTTP client wrapper with error handling */

export interface ApiErrorResponse {
  detail: string | Array<{ msg: string; loc: string[] }>;
  status?: number;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail: unknown = response.statusText;
    try {
      const data = await response.json();
      errorDetail = data.detail || data;
    } catch {
      // Failed to parse JSON error, keep statusText
    }

    const message =
      typeof errorDetail === 'string'
        ? errorDetail
        : `API request failed with status ${response.status}`;

    throw new ApiError(message, response.status, errorDetail);
  }

  // If 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
