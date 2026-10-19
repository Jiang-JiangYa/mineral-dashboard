// Shared dashboard transport; custom query endpoints keep their own cancellation lifecycle.
export async function request(path, options = {}) {
  const response = await fetch('/api/' + path, {
    ...options,
    signal: options.signal || AbortSignal.timeout(20000),
  })
  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const detail = (await response.json()).detail
      if (typeof detail === 'string') message = detail
    } catch {
      // Preserve the status when the response body is not JSON.
    }
    throw new Error(message)
  }
  return response.json()
}

export async function loadDocuments(target = 100) {
  const items = []
  let total = Infinity
  while (items.length < target && items.length < total) {
    const page = await request(
      `documents?limit=${Math.min(1000, target - items.length)}&offset=${items.length}`,
    )
    total = page.total
    if (!page.items.length) break
    items.push(...page.items)
  }
  return { items, total }
}
