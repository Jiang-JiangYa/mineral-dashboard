<script setup>
defineProps({
  records: { type: Array, required: true },
  filter: { type: String, default: 'all' },
  mineral: { type: String, default: 'all' },
})
defineEmits(['update:filter', 'update:mineral', 'open', 'all'])
const filters = [
  { id: 'all', label: '全部' },
  { id: 'news', label: '矿业新闻' },
  { id: 'policy', label: '矿产政策' },
]
</script>

<template>
  <section class="panel feed">
    <div class="panelhead">
      <h2>
        最新情报
        <span>LIVE FEED</span>
      </h2>
      <button @click="$emit('all')">查看全部 ↗</button>
    </div>
    <div class="filters">
      <div>
        <button
          v-for="item in filters"
          :key="item.id"
          :class="{ selected: filter === item.id }"
          @click="$emit('update:filter', item.id)"
        >
          {{ item.label }}
        </button>
      </div>
      <select
        :value="mineral"
        aria-label="矿种筛选"
        @change="$emit('update:mineral', $event.target.value)"
      >
        <option value="all">全部矿种</option>
        <option v-for="name in ['锂', '铜', '稀土', '铁矿石']" :key="name">{{ name }}</option>
      </select>
    </div>
    <article
      v-for="record in records"
      :key="record.id"
      class="item"
      tabindex="0"
      role="button"
      @click="$emit('open', record)"
      @keydown.enter="$emit('open', record)"
      @keydown.space.prevent="$emit('open', record)"
    >
      <div class="meta">
        <span class="tag" :class="record.type">
          {{ record.type === 'policy' ? '矿产政策' : '矿业新闻' }}
        </span>
        <span>{{ record.source }}</span>
        <span style="margin-left: auto">{{ record.date }}</span>
      </div>
      <h3>{{ record.title }}</h3>
      <small>
        {{ record.mineral || '综合矿产' }} /
        {{ record.is_reference ? '历史参考摘要' : '已采集文档' }} ↗
      </small>
    </article>
    <p v-if="!records.length">没有符合筛选条件的文档。可前往数据管线运行采集。</p>
  </section>
</template>
