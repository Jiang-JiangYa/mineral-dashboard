import { onBeforeUnmount, ref } from 'vue'
import { documents } from '../data/demo.js'

export function useQuery() {
  const answer = ref('')
  const loading = ref(false)
  let controller
  async function submit(question, endpoint) {
    const text = question.trim()
    if (!text || loading.value) return
    if (!endpoint) {
      const evidence = documents.filter(record => text.includes(record.mineral)).map(record => `${record.title}（${record.source}，示例）`).join('；')
      answer.value = `演示回答\n\n当前未连接真实检索服务，无法判断“${text}”的实际结论。\n\n正式接入后，系统会按时间、国家和矿种筛选新闻、政策与价格，并返回有来源链接的回答。\n\n可用示例证据：${evidence || '没有匹配的示例证据。'}`
      return
    }
    loading.value = true
    answer.value = '正在检索…'
    controller = new AbortController()
    const requestController = controller
    const timeout = setTimeout(() => requestController.abort(), 20000)
    try {
      const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text }), signal: requestController.signal })
      if (!response.ok) throw new Error(`服务返回 ${response.status}`)
      const result = await response.json()
      if (typeof result.answer !== 'string') throw new Error('响应中缺少 answer 字段')
      answer.value = result.answer
    } catch (error) {
      answer.value = `请求失败：${error.name === 'AbortError' ? '请求超时或已取消' : error.message}。请检查服务地址与跨域设置。`
    } finally {
      clearTimeout(timeout)
      controller = undefined
      loading.value = false
    }
  }
  onBeforeUnmount(() => controller?.abort())
  return { answer, loading, submit }
}
