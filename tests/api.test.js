import { afterEach, expect, it, vi } from 'vitest'
import { loadDocuments, request } from '../src/services/api.js'

afterEach(() => vi.unstubAllGlobals())

it('refreshes more than 1000 loaded records within the backend page limit', async () => {
  const fetchMock = vi.fn(async (url) => {
    const params = new URL(url, 'http://localhost').searchParams
    const limit = Number(params.get('limit'))
    const offset = Number(params.get('offset'))
    expect(limit).toBeLessThanOrEqual(1000)
    return {
      ok: true,
      json: async () => ({
        items: Array.from({ length: limit }, (_, i) => ({ id: offset + i })),
        total: 1500,
      }),
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  const result = await loadDocuments(1100)
  expect(result.items).toHaveLength(1100)
  expect(new Set(result.items.map((row) => row.id)).size).toBe(1100)
  expect(fetchMock).toHaveBeenCalledTimes(2)
})

it('preserves HTTP errors when FastAPI returns structured validation details', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: 'invalid' }] }),
    }),
  )
  await expect(request('documents')).rejects.toThrow('HTTP 422')
})
