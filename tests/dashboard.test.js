import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from '../src/App.vue'
import QueryPanel from '../src/components/QueryPanel.vue'
import { createDocumentsCsv } from '../src/utils/exportCsv.js'

const fixtureDocs = [
  {
    id: 'p1',
    kind: 'policy',
    minerals: ['锂'],
    mineral: '锂',
    title: '澳洲关键矿产战略',
    source: 'TEST',
    date: '2026-01-01',
    text: '隔离测试政策',
    url: 'https://example.org/p1',
  },
  {
    id: 'n1',
    kind: 'news',
    minerals: ['铜'],
    mineral: '铜',
    title: '铜供应测试',
    source: 'TEST',
    date: '2026-01-01',
    text: '隔离测试新闻',
  },
  {
    id: 'p2',
    kind: 'policy',
    minerals: ['稀土'],
    mineral: '稀土',
    title: '稀土政策测试',
    source: 'TEST',
    date: '2026-01-01',
    text: '隔离测试政策',
  },
  {
    id: 'n2',
    kind: 'news',
    minerals: ['铁矿石'],
    mineral: '铁矿石',
    title: '铁矿石测试',
    source: 'TEST',
    date: '2026-01-01',
    text: '隔离测试新闻',
  },
]
const fixturePrices = [
  ...['2026-01-01', '2026-01-02'].map((day, i) => ({
    id: 'cu' + i,
    source: 'TEST',
    market: 'LME',
    instrument: '铜',
    price: String(9000 + i * 100),
    currency: 'USD',
    unit: '吨',
    published_at: day,
    date: day,
    quote_type: 'cash',
    contract: '',
  })),
  ...['2026-01-01', '2026-01-02'].map((day, i) => ({
    id: 'li' + i,
    source: 'TEST',
    market: 'GFEX',
    instrument: '锂',
    price: String(78000 + i * 500),
    currency: 'CNY',
    unit: '吨',
    published_at: day,
    date: day,
    quote_type: 'settlement',
    contract: 'LC2601',
  })),
]
let wrapper
const button = (root, text) => root.findAll('button').find((item) => item.text().includes(text))
beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url) => ({
      ok: true,
      json: async () => {
        if (url.includes('/documents')) return { items: fixtureDocs, total: 4 }
        if (url.includes('/prices')) return { items: fixturePrices }
        if (url.includes('/overview'))
          return {
            coverage: { counts: { news: 2, policy: 2, price: 0 }, total_recent: 4 },
            sources: [],
            job: { status: 'idle' },
          }
        if (url.includes('/runs')) return { items: [] }
        return { answer: '测试服务回答', sources: [] }
      },
    })),
  )
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true
  }
  HTMLDialogElement.prototype.close = function () {
    this.open = false
  }
})
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('dashboard migration', () => {
  it('combines filters, opens a detail, and returns without losing filters', async () => {
    wrapper = mount(App)
    await flushPromises()
    expect(wrapper.findAll('.feed .item')).toHaveLength(4)
    await button(wrapper.find('.filters'), '矿产政策').trigger('click')
    await wrapper.find('select').setValue('锂')
    expect(wrapper.findAll('.feed .item')).toHaveLength(1)
    await wrapper.find('.feed .item').trigger('keydown', { key: 'Enter' })
    expect(wrapper.find('#detail').text()).toContain('澳洲关键矿产战略')
    await button(wrapper, '返回列表').trigger('click')
    expect(wrapper.findAll('.feed .item')).toHaveLength(1)
    await wrapper.find('select').setValue('铜')
    expect(wrapper.find('.feed').text()).toContain('没有符合筛选条件')
  })
  it('navigates every page and changes the price and chart together', async () => {
    wrapper = mount(App)
    await flushPromises()
    const initialValue = wrapper.find('.pricevalue').text()
    await wrapper
      .find('[aria-label="价格序列"]')
      .setValue('TEST / GFEX / 锂 / LC2601 / settlement / CNY / 吨')
    expect(wrapper.find('.pricevalue').text()).toContain('78500')
    expect(wrapper.find('.pricevalue').text()).toContain('CNY / 吨')
    expect(wrapper.find('.pricevalue').text()).not.toBe(initialValue)
    for (const label of ['矿业新闻', '关键矿产政策', '市场价格', '数据管线', '质量评估']) {
      await button(wrapper.find('nav'), label).trigger('click')
      expect(wrapper.find('header b').text()).toBe(label)
      expect(wrapper.find('#detail').exists()).toBe(true)
    }
    await button(wrapper.find('nav'), '智能问答').trigger('click')
    expect(wrapper.find('#overview').attributes('style')).not.toContain('display: none')
  })
  it('retains old endpoint settings and validates new URLs before saving', async () => {
    localStorage.setItem('mineral-query-endpoint', 'https://example.com/query')
    wrapper = mount(App)
    await flushPromises()
    await button(wrapper, '接口设置').trigger('click')
    const input = wrapper.find('[aria-label="接口地址"]')
    expect(input.element.value).toBe('https://example.com/query')
    await input.setValue('javascript:alert(1)')
    await wrapper.find('.settings-form').trigger('submit')
    expect(wrapper.find('[role="alert"]').text()).toContain('HTTP 或 HTTPS')
    expect(localStorage.getItem('mineral-query-endpoint')).toBe('https://example.com/query')
    await input.setValue('')
    await wrapper.find('.settings-form').trigger('submit')
    expect(localStorage.getItem('mineral-query-endpoint')).toBe('')
    expect(wrapper.find('dialog').element.open).toBe(false)
  })
  it('escapes CSV quotes and preserves embedded commas and line breaks', () => {
    const csv = createDocumentsCsv([
      {
        type: 'news',
        mineral: '铜',
        title: '标题,"引用"\n下一行',
        source: '示例',
        date: '2026-10-14',
      },
    ])
    expect(csv.startsWith('\ufeff')).toBe(true)
    expect(csv).toContain('"标题,""引用""\n下一行"')
  })
})

describe('query interface', () => {
  it('renders source links and rejects unsafe schemes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          answer: '有来源的回答',
          sources: [
            {
              id: 'safe',
              title: '真实来源',
              url: 'https://example.org/policy',
              published_at: '2023-07-07',
              is_reference: true,
            },
            { id: 'unsafe', title: '不可执行', url: 'javascript:alert(1)' },
          ],
        }),
      }),
    )
    wrapper = mount(QueryPanel)
    await wrapper.find('input').setValue('查询政策')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.findAll('.citations a')).toHaveLength(1)
    expect(wrapper.find('.citations a').attributes('href')).toBe('https://example.org/policy')
    expect(wrapper.find('.citations').text()).toContain('历史参考摘要')
  })
  it('uses the local backend by default and treats response text as text', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ answer: '<script>alert(1)</script> 后端回答' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    wrapper = mount(QueryPanel)
    await wrapper.find('input').setValue('铜 <script>alert(1)</script>')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/query',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(wrapper.find('#answer').text()).toContain('后端回答')
    expect(wrapper.find('#answer script').exists()).toBe(false)
  })
  it('sends the compatible request and safely displays the response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ answer: '<img src=x onerror=alert(1)>证据回答' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    wrapper = mount(QueryPanel, { props: { endpoint: 'https://example.com/query' } })
    await wrapper.find('input').setValue('  铜价变化  ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith(
      'https://example.com/query',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ question: '铜价变化' }) }),
    )
    expect(wrapper.find('#answer').text()).toContain('证据回答')
    expect(wrapper.find('#answer img').exists()).toBe(false)
    expect(wrapper.find('[type="submit"]').element.disabled).toBe(false)
  })
  it.each([
    [{ ok: false, status: 503 }, '503'],
    [{ ok: true, json: async () => ({ sources: [] }) }, '缺少 answer'],
  ])('shows service errors and allows retry', async (response, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    wrapper = mount(QueryPanel, { props: { endpoint: 'https://example.com/query' } })
    await wrapper.find('input').setValue('查询')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('#answer').text()).toContain(message)
    expect(wrapper.find('[type="submit"]').element.disabled).toBe(false)
  })
  it('aborts after 20 seconds and prevents duplicate submissions', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn(
      (url, { signal }) =>
        new Promise((resolve, reject) =>
          signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))),
        ),
    )
    vi.stubGlobal('fetch', fetchMock)
    wrapper = mount(QueryPanel, { props: { endpoint: 'https://example.com/query' } })
    await wrapper.find('input').setValue('查询')
    await wrapper.find('form').trigger('submit')
    await wrapper.find('form').trigger('submit')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(20000)
    expect(wrapper.find('#answer').text()).toContain('超时')
    expect(wrapper.find('[type="submit"]').element.disabled).toBe(false)
  })
})

describe('live data states', () => {
  it('shows a service failure instead of silently falling back to sample data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    wrapper = mount(App)
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('后端连接失败')
    expect(wrapper.findAll('.feed .item')).toHaveLength(0)
    expect(wrapper.find('.market').text()).toContain('尚无授权行情')
    expect(wrapper.find('.stats').text()).not.toContain('648')
  })
  it('loads database counts and triggers the real evaluation endpoint', async () => {
    wrapper = mount(App)
    await flushPromises()
    expect(wrapper.find('.stats').text()).toContain('新闻 2 · 政策 2 · 价格 0')
    await button(wrapper.find('nav'), '质量评估').trigger('click')
    await button(wrapper, '运行 20 条评估').trigger('click')
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith('/api/eval', expect.objectContaining({ method: 'POST' }))
  })
})
