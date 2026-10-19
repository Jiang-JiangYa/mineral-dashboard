<script setup>
import { nextTick, ref } from 'vue'
import { useQuery } from '../composables/useQuery.js'
const props = defineProps({ endpoint: { type: String, default: '' } })
const question = ref('')
const input = ref(null)
const { answer, sources, loading, submit } = useQuery()
const suggestions = [
  '近 7 天澳洲锂出口政策有何变化？',
  '澳大利亚关键矿产战略对本国加工能力有何目标？',
  '铜价与供应相关新闻',
]
function focus() {
  nextTick(() => input.value?.focus())
}
function suggest(value) {
  question.value = value
  focus()
}
function query() {
  if (!question.value.trim()) return focus()
  submit(question.value, props.endpoint)
}
defineExpose({ focus })
</script>

<template>
  <section class="askbox">
    <div class="asktitle">
      <span>✧</span>
      <div>
        <h2>从一个好问题开始</h2>
        <p>跨来源检索矿业情报，追溯每一条证据</p>
      </div>
      <span class="rag">三源联合检索</span>
    </div>
    <form @submit.prevent="query">
      <input
        ref="input"
        v-model="question"
        placeholder="近 7 天澳洲锂出口政策有何变化？"
        aria-label="查询问题"
      />
      <button type="submit" :disabled="loading">{{ loading ? '检索中…' : '开始检索 ↗' }}</button>
    </form>
    <div class="suggestions">
      <span>试着问</span>
      <button v-for="suggestion in suggestions" :key="suggestion" @click="suggest(suggestion)">
        {{ suggestion }}
      </button>
    </div>
    <div v-if="answer" id="answer" role="status" aria-live="polite">{{ answer }}</div>
    <ol v-if="sources.length" class="citations">
      <li v-for="source in sources" :key="source.id">
        <a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.title }} ↗</a>
        <small>
          · {{ source.published_at?.slice(0, 10)
          }}{{ source.is_reference ? ' · 历史参考摘要' : '' }}
        </small>
      </li>
    </ol>
  </section>
</template>
