/**
 * Thin typed fetch wrapper for the Casefile API (docs/API_PLAN.md §8).
 *
 * - Same-origin session cookie; `X-CSRFToken` from the `csrftoken` cookie on unsafe methods.
 *   (`GET /auth/csrf/` to set the cookie arrives with auth in M5; see `ensureCsrfCookie`.)
 * - Every non-2xx response becomes an `ApiError` built from the error envelope.
 */

export const API_BASE = '/api/v1'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface Envelope {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

function isEnvelope(body: unknown): body is Envelope {
  const error = (body as Envelope | null)?.error
  return typeof error?.code === 'string' && typeof error.message === 'string'
}

let onUnauthorized: (() => void) | null = null

/** Registered by the auth store: what to do when an account-only endpoint returns 401. */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

function readCookie(name: string): string | null {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null
}

/** Ensures the CSRF cookie exists. The `/auth/csrf/` endpoint is planned for M5. */
export async function ensureCsrfCookie(): Promise<void> {
  if (!readCookie('csrftoken')) await request('GET', '/auth/csrf/')
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const headers = new Headers({ Accept: 'application/json' })
  if (body !== undefined) headers.set('Content-Type', 'application/json')
  if (method !== 'GET') {
    const token = readCookie('csrftoken')
    if (token) headers.set('X-CSRFToken', token)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'network_error', "We couldn't reach the server.")
  }

  if (response.status === 204) return undefined as T
  const payload: unknown = await response.json().catch(() => null)

  if (response.ok) return payload as T

  const error = isEnvelope(payload)
    ? new ApiError(
        response.status,
        payload.error.code,
        payload.error.message,
        payload.error.details,
      )
    : new ApiError(response.status, 'server_error', 'Something went wrong on our side.')
  if (response.status === 401) onUnauthorized?.()
  throw error
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string, body?: unknown) => request<T>('DELETE', path, body),
}
