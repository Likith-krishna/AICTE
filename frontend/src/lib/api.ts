const API_BASE = '/api';

/** Error raised for any non-2xx API response. Carries the backend's structured detail when present. */
class ApiError extends Error {
  status: number;
  code?: string;
  fieldErrors?: Record<string, string>;
  failures?: string[];

  constructor(message: string, status: number, extra: Partial<Pick<ApiError, 'code' | 'fieldErrors' | 'failures'>> = {}) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
    Object.assign(this, extra);
  }
}

function getToken(): string | null {
  try {
    return localStorage.getItem('access_token');
  } catch {
    return null;
  }
}

function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string') return new ApiError(detail, status);
  if (Array.isArray(detail)) {
    // FastAPI request-validation errors
    const msg = detail
      .map((d: { msg?: string; loc?: unknown[] }) => `${(d.loc || []).slice(-1)[0] ?? ''}: ${d.msg ?? ''}`)
      .join('; ');
    return new ApiError(msg || 'Invalid request', status, { code: 'REQUEST_INVALID' });
  }
  if (detail && typeof detail === 'object') {
    const d = detail as { message?: string; code?: string; field_errors?: Record<string, string>; failures?: string[] };
    return new ApiError(d.message || `HTTP ${status}`, status, {
      code: d.code,
      fieldErrors: d.field_errors,
      failures: d.failures,
    });
  }
  return new ApiError(`HTTP ${status}`, status);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError('Cannot reach the FlowGuard server. Check your connection and try again.', 0, {
      code: 'NETWORK',
    });
  }

  // A 401 on login means wrong credentials; anywhere else it means the session expired.
  if (response.status === 401 && !path.startsWith('/auth/login')) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new ApiError('Your session has expired. Please sign in again.', 401);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw toApiError(response.status, body);
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: data !== undefined ? JSON.stringify(data) : undefined }),
  put: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'PUT', body: data !== undefined ? JSON.stringify(data) : undefined }),
  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'PATCH', body: data !== undefined ? JSON.stringify(data) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}

export { ApiError };
