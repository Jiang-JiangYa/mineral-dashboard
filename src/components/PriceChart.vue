<script setup>
import { computed, ref } from 'vue'
import { prices } from '../data/demo.js'
const selected = ref(0)
const current = computed(() => prices[selected.value])
const line = computed(() => {
  if (selected.value === 0) return 'M0 135L25 125L50 132L75 95L100 105L125 88L150 98L175 60L200 78L225 62L250 75L275 43L300 55L325 30L350 45L375 20L420 15'
  return 'M' + Array.from({ length: 18 }, (_, index) => `${Math.round(index * 420 / 17)} ${Math.round(138 - index * 6 + Math.sin(index * 1.7 + selected.value) * 15)}`).join('L')
})
</script>

<template>
  <section class="panel market">
    <div class="panelhead"><h2>价格观察</h2><span class="unit">示例行情</span></div>
    <div class="price-tabs"><button v-for="(price, index) in prices" :key="price.mineral" :class="{ selected: selected === index }" @click="selected = index">{{ price.mineral }}</button></div>
    <div class="pricevalue"><span>{{ current.market }} · {{ current.unit }}</span><div><strong>{{ current.price }}</strong><b>{{ current.change }} ↗</b></div></div>
    <svg viewBox="0 0 420 175" role="img" :aria-label="`${current.mineral}示例近30天价格走势`">
      <defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#e8ad63" stop-opacity=".25" /><stop offset="1" stop-color="#e8ad63" stop-opacity="0" /></linearGradient></defs>
      <g stroke="#e9ecec" stroke-dasharray="3 4"><path d="M0 25H420M0 75H420M0 125H420" /></g>
      <path :d="line + 'V175H0Z'" fill="url(#fill)" /><path :d="line" fill="none" stroke="#cc914e" stroke-width="2.5" />
    </svg>
    <div class="axis"><span>09.15</span><span>09.25</span><span>10.05</span><span>10.14</span></div>
    <div class="marketfoot"><span>近 30 天</span><span>价格口径为演示设置</span></div>
  </section>
</template>
