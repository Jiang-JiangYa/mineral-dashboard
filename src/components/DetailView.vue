<script setup>
import SourcesPanel from './SourcesPanel.vue'
import PriceChart from './PriceChart.vue'
defineProps({
  view: { type: String, required: true },
  record: { type: Object, default: null },
  documents: { type: Array, default: () => [] },
  prices: { type: Array, default: () => [] },
  overview: { type: Object, default: () => ({}) },
  runs: { type: Array, default: () => [] },
  acting: Boolean,
  message: String,
})
defineEmits(['open', 'back', 'collect', 'evaluate'])
const percent = (value) => (value == null ? '未评估' : (value * 100).toFixed(1) + '%')
</script>
<template>
  <section id="detail">
    <div v-if="record" class="panel document-detail">
      <button class="outline" @click="$emit('back')">← 返回列表</button>
      <p>
        <span class="tag" :class="record.type">
          {{ record.mineral || '综合矿产' }} ·
          {{ record.is_reference ? '历史参考摘要' : '采集记录' }}
        </span>
      </p>
      <h1>{{ record.title }}</h1>
      <p>{{ record.source }} | {{ record.date }}</p>
      <p class="document-text">{{ record.text }}</p>
      <a v-if="record.url" :href="record.url" target="_blank" rel="noopener noreferrer">
        查看原始来源 ↗
      </a>
    </div>
    <section v-else-if="view === 'news' || view === 'policy'" class="panel">
      <article
        v-for="document in documents.filter((item) => item.type === view)"
        :key="document.id"
        class="item"
        role="button"
        tabindex="0"
        @click="$emit('open', document)"
        @keydown.enter="$emit('open', document)"
        @keydown.space.prevent="$emit('open', document)"
      >
        <div class="meta">
          {{ document.source }} · {{ document.date }} ·
          {{ document.is_reference ? '历史参考摘要' : '采集文档' }}
        </div>
        <h3>{{ document.title }}</h3>
        <p>{{ document.text.slice(0, 180) }}…</p>
      </article>
      <p v-if="!documents.some((item) => item.type === view)">暂无此类文档，请先运行采集或导入。</p>
    </section>
    <section v-else-if="view === 'prices'" class="panel table-scroll">
      <PriceChart :prices="prices" />
      <h2>行情观测记录</h2>
      <p>金额保留原始精度；不同市场、合约、币种、单位与口径不混为同一序列。</p>
      <table>
        <thead>
          <tr>
            <th>品种/合约</th>
            <th>市场/口径</th>
            <th>时间</th>
            <th>价格/单位</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="price in prices" :key="price.id">
            <td>{{ price.instrument }} {{ price.contract }}</td>
            <td>{{ price.market }} / {{ price.quote_type }}</td>
            <td>{{ price.published_at }}</td>
            <td>{{ price.price }} {{ price.currency }}/{{ price.unit }}</td>
          </tr>
        </tbody>
      </table>
    </section>
    <section v-else-if="view === 'pipeline'" class="panel">
      <div class="panelhead">
        <h2>采集 → 清洗 → 去重 → 向量化 → 入库</h2>
        <button
          class="outline"
          :disabled="acting || overview.job?.status === 'running'"
          @click="$emit('collect')"
        >
          {{ overview.job?.status === 'running' ? '采集中…' : '启动采集' }}
        </button>
      </div>
      <p>状态：{{ overview.job?.status || 'idle' }} · {{ overview.job?.error || message }}</p>
      <p>
        原始记录 {{ overview.coverage?.total_documents || 0 }} 条，向量切片
        {{ overview.coverage?.chunks || 0 }} 条。切片不作为新增原始记录计数。
      </p>
      <p>
        近 30 天缺口：新闻 {{ overview.coverage?.deficits?.news ?? 200 }} / 政策
        {{ overview.coverage?.deficits?.policy ?? 200 }} / 价格
        {{ overview.coverage?.deficits?.price ?? 200 }}。
      </p>
      <SourcesPanel :sources="overview.sources" />
      <h3>最近运行记录</h3>
      <article v-for="run in runs" :key="run.id" class="item">
        <b>{{ run.status }}</b>
        · {{ run.started_at }}
        <ul>
          <li v-for="source in run.report.sources" :key="source.id">
            {{ source.name }}：{{ source.status }}，新增 {{ source.inserted || 0 }} 条；{{
              source.message || source.errors?.[0]
            }}
            <details v-if="source.errors?.length || source.excluded">
              <summary>排除与错误详情</summary>
              <pre>{{
                JSON.stringify({ excluded: source.excluded, errors: source.errors }, null, 2)
              }}</pre>
            </details>
          </li>
        </ul>
      </article>
      <p v-if="!runs.length">尚无采集作业记录。</p>
    </section>
    <section v-else-if="view === 'eval'" class="panel table-scroll">
      <div class="panelhead">
        <h2>检索与回答评估</h2>
        <button class="outline" :disabled="acting" @click="$emit('evaluate')">
          运行 20 条评估
        </button>
      </div>
      <p>{{ message }}</p>
      <template v-if="overview.evaluation">
        <p>{{ overview.evaluation.corpus }}</p>
        <p>生成时间：{{ overview.evaluation.created_at }} · {{ overview.evaluation.encoder }}</p>
        <table>
          <thead>
            <tr>
              <th>指标</th>
              <th>结果</th>
              <th>定义</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Recall@5</td>
              <td>{{ percent(overview.evaluation.recall_at_5) }}</td>
              <td>前五个原始文档覆盖标注证据的比例</td>
            </tr>
            <tr>
              <td>回答忠实度</td>
              <td>{{ percent(overview.evaluation.answer_faithfulness) }}</td>
              <td>抽取式断言在所引用证据中的精确支持率</td>
            </tr>
            <tr>
              <td>标准答案命中</td>
              <td>{{ percent(overview.evaluation.answer_accuracy) }}</td>
              <td>回答是否含预期事实短语</td>
            </tr>
          </tbody>
        </table>
        <p>
          当前基准仅覆盖 DISR
          历史政策参考摘要，不能代表近期三源泛化效果。抽取式忠实度高不等于回答完整或问题已解决。
        </p>
        <article v-for="row in overview.evaluation.results" :key="row.question" class="item">
          <h3>{{ row.question }}</h3>
          <p>标准答案：{{ row.expected_answer }}</p>
          <small>
            Recall@5 {{ percent(row.recall_at_5) }} · 引用支持率 {{ percent(row.faithfulness) }}
          </small>
        </article>
      </template>
      <p v-else>尚未运行评估。先执行 python -m pipeline bootstrap 初始化历史参考资料。</p>
    </section>
  </section>
</template>
