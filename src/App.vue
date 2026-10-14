<script setup>
import { computed, nextTick, ref } from 'vue'
import AppSidebar from './components/AppSidebar.vue'
import QueryPanel from './components/QueryPanel.vue'
import StatsCards from './components/StatsCards.vue'
import NewsFeed from './components/NewsFeed.vue'
import PriceChart from './components/PriceChart.vue'
import SourcesPanel from './components/SourcesPanel.vue'
import DetailView from './components/DetailView.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import { documents, navigation } from './data/demo.js'
import { exportDocuments } from './utils/exportCsv.js'

const view = ref('overview')
const selectedRecord = ref(null)
const filter = ref('all')
const mineral = ref('all')
const queryPanel = ref(null)
const settings = ref(null)
let savedEndpoint = ''
try { savedEndpoint = localStorage.getItem('mineral-query-endpoint') || '' } catch { /* Demo mode also works when browser storage is unavailable. */ }
const endpoint = ref(savedEndpoint)
const label = computed(() => navigation.find(item => item.id === view.value)?.label || '情报总览')
const showOverview = computed(() => !selectedRecord.value && ['overview', 'ask'].includes(view.value))
const records = computed(() => documents.filter(record => (filter.value === 'all' || record.type === filter.value) && (mineral.value === 'all' || record.mineral === mineral.value)))
const exportRecords = computed(() => selectedRecord.value ? [selectedRecord.value] : ['news', 'policy'].includes(view.value) ? documents.filter(record => record.type === view.value) : records.value)
async function navigate(value) {
  view.value = value
  selectedRecord.value = null
  if (value === 'ask') { await nextTick(); queryPanel.value?.focus() }
}
</script>

<template>
  <AppSidebar :active="view" @navigate="navigate" @settings="settings.open()" />
  <main>
    <header><div>工作台 <span>/</span> <b>{{ label }}</b></div><div class="header-right"><span class="demo">示例数据</span><span>◷　2026 年 10 月 14 日</span></div></header>
    <section class="page">
      <div class="title-row"><div><div class="eyebrow">YOUR EDGE IN MINERAL MARKETS</div><h1>{{ selectedRecord ? '情报详情' : label }}<span class="dot">.</span></h1><p>{{ selectedRecord ? '示例内容 · 用于展示文档阅读与来源追溯' : view === 'overview' ? '连接新闻、政策与价格，让每一次判断都有据可循。' : '演示工作空间 · 接入真实服务后可展示生产数据' }}</p></div><button class="outline" @click="exportDocuments(exportRecords)">↓　导出数据</button></div>
      <div class="notice">◉　交互演示 · 下列新闻、政策、价格与评估结果均为示例，未连接实时采集管线。</div>
      <div v-show="showOverview" id="overview">
        <QueryPanel ref="queryPanel" :endpoint="endpoint" />
        <StatsCards />
        <div class="grid"><NewsFeed v-model:filter="filter" v-model:mineral="mineral" :records="records" @open="selectedRecord = $event" @all="navigate('news')" /><PriceChart /></div>
        <SourcesPanel @navigate="navigate" />
      </div>
      <DetailView v-if="!showOverview" :view="view" :record="selectedRecord" @open="selectedRecord = $event" @back="selectedRecord = null" />
      <footer><span>矿观 · 将分散的信息，转化为可追溯的洞察</span><span>数据演示版 / V0.2 · Vue 3</span></footer>
    </section>
  </main>
  <SettingsDialog ref="settings" :endpoint="endpoint" @save="endpoint = $event" />
</template>
