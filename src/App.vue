<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref } from 'vue'
import AppSidebar from './components/AppSidebar.vue'
import QueryPanel from './components/QueryPanel.vue'
import StatsCards from './components/StatsCards.vue'
import NewsFeed from './components/NewsFeed.vue'
import PriceChart from './components/PriceChart.vue'
import SourcesPanel from './components/SourcesPanel.vue'
import DetailView from './components/DetailView.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import { navigation } from './data/navigation.js'
import { exportDocuments } from './utils/exportCsv.js'

const view = ref('overview'), selectedRecord = ref(null), filter = ref('all'), mineral = ref('all')
const queryPanel = ref(null), settings = ref(null), documents = ref([]), prices = ref([]), overview = ref({}), runs = ref([])
const total = ref(0), loading = ref(false), error = ref(''), actionMessage = ref(''), acting = ref(false)
let savedEndpoint = ''
try { savedEndpoint = localStorage.getItem('mineral-query-endpoint') || '' } catch { /* Browser storage can be disabled. */ }
const endpoint = ref(savedEndpoint)
const label = computed(() => navigation.find(item => item.id === view.value)?.label || '情报总览')
const showOverview = computed(() => !selectedRecord.value && ['overview', 'ask'].includes(view.value))
const records = computed(() => documents.value.filter(record => record.kind !== 'price' && (filter.value === 'all' || record.type === filter.value) && (mineral.value === 'all' || record.minerals?.includes(mineral.value))))
const exportRecords = computed(() => selectedRecord.value ? [selectedRecord.value] : view.value === 'prices' ? prices.value : ['news', 'policy'].includes(view.value) ? documents.value.filter(record => record.type === view.value) : records.value)
async function request(path, options) {
  const response = await fetch('/api/' + path, { ...options, signal: AbortSignal.timeout(20000) })
  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try { message = (await response.json()).detail || message } catch { /* Keep HTTP error. */ }
    throw new Error(message)
  }
  return response.json()
}
const normalize = row => ({ ...row, type: row.kind })
async function refresh() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const [summary, docs, quotes, history] = await Promise.all([request('overview'), request(`documents?limit=${Math.max(100, documents.value.length)}`), request('prices'), request('runs')])
    overview.value = summary
    documents.value = docs.items.map(normalize)
    total.value = docs.total
    prices.value = quotes.items.map(normalize)
    runs.value = history.items
  } catch (err) { error.value = `后端连接失败：${err.message}。请确认 FastAPI 服务已启动。` }
  finally { loading.value = false }
}
async function loadMore() {
  try {
    const result = await request(`documents?limit=100&offset=${documents.value.length}`)
    const byId = new Map(documents.value.map(row => [row.id, row]))
    result.items.forEach(row => byId.set(row.id, normalize(row)))
    documents.value = [...byId.values()]
  } catch (err) { error.value = err.message }
}
async function action(name) {
  if (acting.value) return
  acting.value = true
  actionMessage.value = ''
  try {
    const result = await request(name, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: name === 'collect' ? '{}' : undefined })
    actionMessage.value = name === 'collect' ? result.message : `评估完成：${result.questions} 条问答`
    await refresh()
  } catch (err) { actionMessage.value = `操作失败：${err.message}。配置管理令牌后请通过命令行运行管理操作。` }
  finally { acting.value = false }
}
async function navigate(value) {
  view.value = value
  selectedRecord.value = null
  if (value === 'ask') { await nextTick(); queryPanel.value?.focus() }
}
let timer
onMounted(() => { refresh(); timer = setInterval(() => { if (overview.value.job?.status === 'running') refresh() }, 5000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <AppSidebar :active="view" @navigate="navigate" @settings="settings.open()" />
  <main>
    <header><div>工作台 <span>/</span> <b>{{ label }}</b></div><div class="header-right"><button @click="settings.open()">接口设置</button><span class="demo">{{ loading ? '读取中' : error ? '连接异常' : '本地数据服务' }}</span><button @click="refresh" :disabled="loading">刷新 ↻</button></div></header>
    <section class="page">
      <div class="title-row"><div><div class="eyebrow">YOUR EDGE IN MINERAL MARKETS</div><h1>{{ selectedRecord ? '情报详情' : label }}<span class="dot">.</span></h1><p>连接新闻、政策与价格，让每一次判断都有据可循。</p></div><button class="outline" @click="exportDocuments(exportRecords)">↓　导出已加载数据</button></div>
      <div v-if="error" class="notice" role="alert">{{ error }} <button @click="refresh">重试</button></div>
      <div v-else class="notice">◉　近 30 天按原始记录验收：每类至少 200 条。历史参考摘要不计入数量；缺口和未授权来源会如实显示。</div>
      <div v-show="showOverview" id="overview">
        <QueryPanel ref="queryPanel" :endpoint="endpoint" />
        <StatsCards :coverage="overview.coverage" :evaluation="overview.evaluation" />
        <div class="grid"><NewsFeed v-model:filter="filter" v-model:mineral="mineral" :records="records" @open="selectedRecord = $event" @all="navigate('news')" /><PriceChart :prices="prices" /></div>
        <SourcesPanel :sources="overview.sources" @navigate="navigate" />
      </div>
      <DetailView v-if="!showOverview" :view="view" :record="selectedRecord" :documents="documents" :prices="prices" :overview="overview" :runs="runs" :acting="acting" :message="actionMessage" @open="selectedRecord = $event" @back="selectedRecord = null" @collect="action('collect')" @evaluate="action('eval')" />
      <p class="loaded-count">已加载 {{ documents.length }} / {{ total }} 条记录 <button v-if="documents.length < total" @click="loadMore">加载更多</button></p>
      <footer><span>矿观 · 将分散的信息，转化为可追溯的洞察</span><span>V0.3 · Vue 3 + FastAPI + sqlite-vec</span></footer>
    </section>
  </main>
  <SettingsDialog ref="settings" :endpoint="endpoint" @save="endpoint = $event" />
</template>
