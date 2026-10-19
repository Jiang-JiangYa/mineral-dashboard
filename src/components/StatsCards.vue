<script setup>
import { computed } from 'vue'
const props = defineProps({
  coverage: { type: Object, default: () => ({}) },
  evaluation: { type: Object, default: null },
})
const count = computed(() => props.coverage.counts || {})
const percent = (value) => (value == null ? '—' : (value * 100).toFixed(1))
</script>
<template>
  <div class="stats">
    <article>
      <span>
        入库原始记录
        <i>近 30 天</i>
      </span>
      <strong>
        {{ coverage.total_recent ?? '—' }}
        <small>条</small>
      </strong>
      <div>
        新闻 {{ count.news || 0 }} · 政策 {{ count.policy || 0 }} · 价格 {{ count.price || 0 }}
      </div>
      <div>目标每类 200 条 · {{ coverage.passed ? '已达标' : '尚有缺口' }}</div>
    </article>
    <article>
      <span>来源类别覆盖</span>
      <strong>
        {{ Object.values(count).filter((value) => value > 0).length }}
        <small>/ 3 类</small>
      </strong>
      <div>历史参考 {{ coverage.reference_documents || 0 }} 条，单独统计</div>
    </article>
    <article>
      <span>
        参考集召回率
        <i>Recall@5</i>
      </span>
      <strong>
        {{ percent(evaluation?.recall_at_5) }}
        <small>%</small>
      </strong>
      <div>{{ evaluation ? `${evaluation.questions} 条历史政策问答` : '尚未运行评估' }}</div>
    </article>
    <article>
      <span>原文引用支持率</span>
      <strong>
        {{ percent(evaluation?.answer_faithfulness) }}
        <small>%</small>
      </strong>
      <div>抽取式忠实度基线 · 非独立模型裁判</div>
    </article>
  </div>
</template>
