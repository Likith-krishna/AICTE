import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError, errorMessage } from './api';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('ApiError', () => {
  it('carries status, code, field errors and failures', () => {
    const err = new ApiError('Preconditions not met', 422, {
      code: 'PRECONDITION_FAILED',
      failures: ['Remarks required.'],
    });
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('ApiError');
    expect(err.message).toBe('Preconditions not met');
    expect(err.status).toBe(422);
    expect(err.code).toBe('PRECONDITION_FAILED');
    expect(err.failures).toEqual(['Remarks required.']);
  });
});

describe('errorMessage', () => {
  it('returns an ApiError\'s own message', () => {
    expect(errorMessage(new ApiError('Nope', 403))).toBe('Nope');
  });

  it('falls back to a plain Error message', () => {
    expect(errorMessage(new Error('boom'))).toBe('boom');
  });

  it('uses the fallback for anything else', () => {
    expect(errorMessage('a string', 'default')).toBe('default');
    expect(errorMessage(undefined)).toBe('Something went wrong');
  });
});

describe('api requests', () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('attaches the stored bearer token and returns parsed JSON on success', async () => {
    localStorage.setItem('access_token', 'tok123');
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.get<{ ok: boolean }>('/health');

    expect(result).toEqual({ ok: true });
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok123');
  });

  it('raises a NETWORK ApiError when fetch itself rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    await expect(api.get('/health')).rejects.toMatchObject({ code: 'NETWORK', status: 0 });
  });

  it('turns a FastAPI structured error detail into an ApiError with failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      jsonResponse(422, { detail: { message: 'Preconditions not met', code: 'PRECONDITION_FAILED', failures: ['Remarks required.'] } }),
    ));

    await expect(api.post('/applications/1/transition', {})).rejects.toMatchObject({
      message: 'Preconditions not met',
      status: 422,
      code: 'PRECONDITION_FAILED',
      failures: ['Remarks required.'],
    });
  });

  it('turns a FastAPI validation-error array into a readable message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      jsonResponse(422, { detail: [{ loc: ['body', 'email'], msg: 'field required' }] }),
    ));

    await expect(api.post('/auth/login', {})).rejects.toMatchObject({
      status: 422,
      code: 'REQUEST_INVALID',
      message: 'email: field required',
    });
  });

  it('clears the session and redirects on a 401 outside the login endpoint', async () => {
    localStorage.setItem('access_token', 'tok123');
    localStorage.setItem('user', '{}');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(401, { detail: 'expired' })));

    const win = window as unknown as { location: unknown };
    const originalLocation = win.location;
    // jsdom's window.location.href setter throws "not implemented (navigation)";
    // replace it with a plain writable stub for this one assertion.
    delete win.location;
    win.location = { href: '' };

    await expect(api.get('/applications')).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem('access_token')).toBeNull();
    expect((win.location as { href: string }).href).toBe('/login');

    win.location = originalLocation;
  });
});
