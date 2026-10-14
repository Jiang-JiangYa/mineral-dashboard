<script setup>
import { documents, prices } from '../data/demo.js'
defineProps({ view: { type: String, required: true }, record: { type: Object, default: null } })
defineEmits(['open', 'back'])
</script>

<template>
  <section id="detail">
    <div v-if="record" class="panel">
      <button class="outline" @click="$emit('back')">← 返回列表</button>
      <p><span class="tag" :class="record.type">{{ record.mineral }} · 示例</span></p>
      <h1>{{ record.title }}</h1><p>{{ record.source }}　|　{{ record.date }}</p><p>{{ record.text }}</p>
      <p>这不是经过采集验证的真实新闻或政策，不能作为研究结论的依据。</p>
      <a v-if="record.url" :href="record.url" target="_blank" rel="noopener">访问来源首页 ↗</a><p v-else>演示记录未配置来源链接。</p>
    </div>
    <section v-else-if="view === 'news' || view === 'policy'" class="panel">
      <article v-for="document in documents.filter(item => item.type === view)" :key="document.id" class="item" role="button" tabindex="0" @click="$emit('open', document)" @keydown.enter="$emit('open', document)" @keydown.space.prevent="$emit('open', document)">
        <div class="meta">{{ document.source }} · {{ document.date }} · 示例</div><h3>{{ document.title }}</h3><p>{{ document.text }}</p>
      </article>
    </section>
    <section v-else-if="view === 'prices'" class="panel">
      <h2>市场价格 · 示例</h2><p>所有价格均为界面演示数值，未接入行情授权服务。</p>
      <table><thead><tr><th>品种</th><th>市场 / 口径</th><th>价格</th><th>单位</th></tr></thead><tbody><tr v-for="price in prices" :key="price.mineral"><td>{{ price.mineral }}</td><td>{{ price.market }}</td><td>{{ price.price }}</td><td>{{ price.unit }}</td></tr></tbody></table>
    </section>
    <section v-else-if="view === 'pipeline'" class="panel">
      <h2>采集 → 清洗 → 去重 → 向量化 → 入库</h2><p>当前为前端演示。采集作业未运行，648 条为示例统计。</p>
      <table><thead><tr><th>来源</th><th>采集要求</th><th>当前状态</th></tr></thead><tbody><tr><td>新闻</td><td>RSS + 正文抽取</td><td>待接入</td></tr><tr><td>政策</td><td>发布机构 + 政策条款</td><td>待核实近30天文档量</td></tr><tr><td>价格</td><td>品种、日期、数值、单位</td><td>待授权并确认锂价格市场</td></tr></tbody></table>
      <p>建议主键：来源 + 规范化 URL；价格使用市场 + 品种 + 合约 + 时间 + 口径。内容哈希用于识别重复文档。</p>
    </section>
    <section v-else-if="view === 'eval'" class="panel">
      <h2>质量评估 · 示例报告</h2><p>下列指标是页面演示值，尚未执行真实检索与问答评估。</p>
      <table><thead><tr><th>指标</th><th>示例结果</th><th>评估方式</th></tr></thead><tbody><tr><td>Recall@5</td><td>85.0%</td><td>检查前5个结果对标注证据的覆盖</td></tr><tr><td>回答忠实度</td><td>92.5%</td><td>逐项检查回答是否得到证据支持</td></tr><tr><td>标准问答</td><td>20 条（规划）</td><td>接入数据后人工核验并冻结基准</td></tr></tbody></table>
    </section>
  </section>
</template>
