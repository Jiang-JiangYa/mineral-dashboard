import { onBeforeUnmount, ref } from 'vue'

export function useQuery() {
  const answer = ref('')
  const loading = ref(false)
  const sources = ref([])
  let controller
  async function submit(question, endpoint) {
    const text = question.trim()
    if (!text || loading.value) return
    sources.value = []
    loading.value = true
    answer.value = '正在检索…'
    controller = new AbortController()
    const requestController = controller
    const timeout = setTimeout(() => requestController.abort(), 20000)
    try {
      const response = await fetch(endpoint || '/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
        signal: requestController.signal,
      })
      if (!response.ok) throw new Error(`服务返回 ${response.status}`)
      const result = await response.json()
      if (typeof result.answer !== 'string') throw new Error('响应中缺少 answer 字段')
      answer.value = result.answer
      sources.value = (Array.isArray(result.sources) ? result.sources : []).filter((source) =>
        /^https?:\/\//i.test(source.url),
      )
    } catch (error) {
      answer.value = `请求失败：${error.name === 'AbortError' ? '请求超时或已取消' : error.message}。请检查服务地址与跨域设置。`
    } finally {
      clearTimeout(timeout)
      controller = undefined
      loading.value = false
    }
  }
  onBeforeUnmount(() => controller?.abort())
  return { answer, sources, loading, submit }
}
