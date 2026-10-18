<script setup>
defineProps({ sources: { type: Array, default: () => [] } })
defineEmits(['navigate'])
const labels = { completed: '已完成', completed_with_gaps: '存在缺口', failed: '失败', needs_configuration: '待配置/授权', not_run: '未运行', running: '采集中' }
const description = source => source.last_run?.errors?.length ? '访问受限或连接失败，详见数据管线。' : source.last_run?.message || (source.configured ? '已配置来源，等待采集。' : '需要补充订阅地址或行情授权。')
</script>
<template>
  <section class="panel sources">
    <div class="panelhead"><h2>三源采集管线</h2><button @click="$emit('navigate', 'pipeline')">查看管线 ↗</button></div>
    <div class="sourcegrid"><article v-for="source in sources" :key="source.id"><div class="sourceicon">◎</div><div><h3>{{ source.name }} <span class="amber">{{ labels[source.status] || source.status }}</span></h3><p>{{ ({news:'新闻',policy:'政策',price:'价格'})[source.kind] }} · {{ source.last_run?.accepted ?? 0 }} 条通过本次校验</p><small>{{ description(source) }}</small></div></article></div>
  </section>
</template>
