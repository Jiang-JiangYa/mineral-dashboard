import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from '../src/App.vue'
import QueryPanel from '../src/components/QueryPanel.vue'
import { createDocumentsCsv } from '../src/utils/exportCsv.js'

let wrapper
const button = (root, text) => root.findAll('button').find(item => item.text().includes(text))
beforeEach(() => {
  localStorage.clear()
  HTMLDialogElement.prototype.showModal = function () { this.open = true }
  HTMLDialogElement.prototype.close = function () { this.open = false }
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.unstubAllGlobals(); vi.useRealTimers() })

describe('dashboard migration', () => {
  it('combines filters, opens a detail, and returns without losing filters', async () => {
    wrapper = mount(App)
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
    const initialPath = wrapper.find('.market svg > path:last-child').attributes('d')
    await button(wrapper.find('.price-tabs'), '锂').trigger('click')
    expect(wrapper.find('.pricevalue').text()).toContain('78,500.00')
    expect(wrapper.find('.pricevalue').text()).toContain('CNY / 吨')
    expect(wrapper.find('.market svg > path:last-child').attributes('d')).not.toBe(initialPath)
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
    const csv = createDocumentsCsv([{ type: 'news', mineral: '铜', title: '标题,"引用"\n下一行', source: '示例', date: '2026-10-14' }])
    expect(csv.startsWith('\ufeff')).toBe(true)
    expect(csv).toContain('"标题,""引用""\n下一行"')
  })
})

describe('query interface', () => {
  it('does not fetch in demo mode and treats question text as text', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    wrapper = mount(QueryPanel)
    await wrapper.find('input').setValue('铜 <script>alert(1)</script>')
    await wrapper.find('form').trigger('submit')
    expect(fetchMock).not.toHaveBeenCalled()
    expect(wrapper.find('#answer').text()).toContain('演示回答')
    expect(wrapper.find('#answer script').exists()).toBe(false)
  })
  it('sends the compatible request and safely displays the response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ answer: '<img src=x onerror=alert(1)>证据回答' }) })
    vi.stubGlobal('fetch', fetchMock)
    wrapper = mount(QueryPanel, { props: { endpoint: 'https://example.com/query' } })
    await wrapper.find('input').setValue('  铜价变化  ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith('https://example.com/query', expect.objectContaining({ method: 'POST', body: JSON.stringify({ question: '铜价变化' }) }))
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
    const fetchMock = vi.fn((url, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))))
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
