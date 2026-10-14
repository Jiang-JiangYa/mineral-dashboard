<script setup>
import { nextTick, ref } from 'vue'
import { useQuery } from '../composables/useQuery.js'
const props = defineProps({ endpoint: { type: String, default: '' } })
const question = ref('')
const input = ref(null)
const { answer, loading, submit } = useQuery()
const suggestions = ['澳洲锂出口政策变化', '铜价与供应相关新闻', '中国稀土行业动态']
function focus() { nextTick(() => input.value?.focus()) }
function suggest(value) { question.value = value; focus() }
function query() { if (!question.value.trim()) return focus(); submit(question.value, props.endpoint) }
defineExpose({ focus })
</script>

<template>
  <section class="askbox">
    <div class="asktitle"><span>✧</span><div><h2>从一个好问题开始</h2><p>跨来源检索矿业情报，追溯每一条证据</p></div><span class="rag">三源联合检索</span></div>
    <form @submit.prevent="query"><input ref="input" v-model="question" placeholder="近 7 天澳洲锂出口政策有何变化？" aria-label="查询问题" /><button type="submit" :disabled="loading">{{ loading ? '检索中…' : '开始检索　↗' }}</button></form>
    <div class="suggestions"><span>试着问</span><button v-for="suggestion in suggestions" :key="suggestion" @click="suggest(suggestion)">{{ suggestion }}</button></div>
    <div v-if="answer" id="answer" role="status" aria-live="polite">{{ answer }}</div>
  </section>
</template>
