import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, setUnauthorizedHandler } from '@/api/client'

function jsonResponse(status: number, body: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api client', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    document.cookie = 'csrftoken=abc123; path=/'
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
    setUnauthorizedHandler(null)
  })

  it('GETs JSON from /api/v1 with same-origin credentials and no CSRF header', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { status: 'ok' }))
    await expect(api.get('/health/')).resolves.toEqual({ status: 'ok' })
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/v1/health/')
    expect(init?.credentials).toBe('same-origin')
    expect(new Headers(init?.headers).get('X-CSRFToken')).toBeNull()
  })

  it.each(['post', 'put', 'patch', 'delete'] as const)(
    '%s sends the CSRF token and a JSON body',
    async (method) => {
      fetchMock.mockResolvedValue(jsonResponse(200, {}))
      await api[method]('/things/', { a: 1 })
      const init = fetchMock.mock.calls[0]![1]!
      const headers = new Headers(init.headers)
      expect(init.method).toBe(method.toUpperCase())
      expect(headers.get('X-CSRFToken')).toBe('abc123')
      expect(headers.get('Content-Type')).toBe('application/json')
      expect(init.body).toBe('{"a":1}')
    },
  )

  it('returns undefined for 204 No Content', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))
    await expect(api.post('/seen/', { items: [] })).resolves.toBeUndefined()
  })

  it('parses the error envelope into an ApiError', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(422, {
        error: { code: 'action_unavailable', message: 'Not available.', details: { key: 'x' } },
      }),
    )
    const error = await api.post('/actions/', {}).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 422,
      code: 'action_unavailable',
      message: 'Not available.',
      details: { key: 'x' },
    })
  })

  it('maps a non-envelope error body to server_error', async () => {
    fetchMock.mockResolvedValue(new Response('<html>Bad gateway</html>', { status: 502 }))
    await expect(api.get('/x/')).rejects.toMatchObject({ status: 502, code: 'server_error' })
  })

  it('maps a network failure to network_error (status 0)', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(api.get('/x/')).rejects.toMatchObject({ status: 0, code: 'network_error' })
  })

  it('calls the unauthorized handler on 401', async () => {
    const onUnauthorized = vi.fn<() => void>()
    setUnauthorizedHandler(onUnauthorized)
    fetchMock.mockResolvedValue(
      jsonResponse(401, { error: { code: 'not_authenticated', message: 'Log in.', details: {} } }),
    )
    await expect(api.get('/me/export/')).rejects.toMatchObject({ code: 'not_authenticated' })
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })
})
