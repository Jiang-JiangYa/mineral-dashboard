<script setup>
import { computed, ref } from 'vue'
const props = defineProps({ prices: { type: Array, default: () => [] } })
const selected = ref('')
const seriesKey = row => [row.source, row.market, row.instrument, row.contract, row.quote_type, row.currency, row.unit].join(' / ')
const groups = computed(() => [...new Set(props.prices.map(seriesKey))])
const active = computed(() => groups.value.includes(selected.value) ? selected.value : groups.value[0])
const points = computed(() => props.prices.filter(row => seriesKey(row) === active.value).slice().sort((a, b) => a.published_at.localeCompare(b.published_at)))
const current = computed(() => points.value.at(-1))
const line = computed(() => {
  const values = points.value.map(row => Number(row.price))
  const min = Math.min(...values), max = Math.max(...values), range = max - min || 1
  return values.map((value, i) => `${i ? 'L' : 'M'}${values.length === 1 ? 210 : i * 420 / (values.length - 1)} ${145 - (value - min) * 120 / range}`).join('')
})
</script>
<template>
  <section class="panel market">
    <div class="panelhead"><h2>价格观察</h2><span class="unit">原始报价 · 按口径分组</span></div>
    <template v-if="current">
      <select v-model="selected" aria-label="价格序列"><option value="" disabled>选择行情序列</option><option v-for="group in groups" :key="group" :value="group">{{ group }}</option></select>
      <div class="pricevalue"><span>{{ active }}</span><div><strong>{{ current.price }}</strong></div></div>
      <svg v-if="points.length > 1" viewBox="0 0 420 175" role="img" :aria-label="`${current.instrument}实际价格走势`"><g stroke="#e9ecec" stroke-dasharray="3 4"><path d="M0 25H420M0 75H420M0 125H420" /></g><path :d="line" fill="none" stroke="#cc914e" stroke-width="2.5" /></svg>
      <p v-else>仅一条观测值，暂不绘制趋势。</p>
      <div class="axis"><span>{{ points[0].date }}</span><span>{{ current.date }}</span></div><p>{{ points.length }} 条观测 · <a :href="current.url" target="_blank" rel="noopener">来源 ↗</a></p>
    </template>
    <div v-else class="empty-state"><h3>尚无授权行情</h3><p>配置 LME、上海钢联数据接口，或导入已获授权的 CSV 后显示真实价格。</p><p>碳酸锂期货属于 GFEX，题目中的 SHFE 锂需先确认口径。</p></div>
  </section>
</template>
