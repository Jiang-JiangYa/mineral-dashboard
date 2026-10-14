// Demonstration records only; not verified news or market data.
export const documents = [
  { id: 'policy-lithium', type: 'policy', mineral: '锂', title: '澳洲关键矿产战略：锂产业链与出口支持措施', source: '澳洲 DISR', date: '2026-10-14', text: '演示文档：展示政策发布机构、适用矿种及政策变化的结构化摘要。', url: 'https://www.industry.gov.au/' },
  { id: 'news-copper', type: 'news', mineral: '铜', title: '全球铜矿供应与需求：市场关注新增产能进展', source: 'MINING.COM', date: '2026-10-14', text: '演示文档：汇总铜矿项目、供应预期及市场关注点。', url: 'https://www.mining.com/' },
  { id: 'policy-rare-earth', type: 'policy', mineral: '稀土', title: '稀土产业发展动态：资源利用与产业链协同', source: '中国稀土集团', date: '2026-10-13', text: '演示文档：展示稀土政策及产业动态的采集和分类效果。', url: null },
  { id: 'news-iron', type: 'news', mineral: '铁矿石', title: '铁矿石市场观察：港口库存与钢厂采购需求', source: 'S&P Global', date: '2026-10-13', text: '演示文档：记录市场新闻的来源、发布日期和矿种标签。', url: 'https://www.spglobal.com/' },
]
export const prices = [
  { mineral: '铜', market: 'LME 铜', price: '9,842.50', change: '+1.24%', unit: 'USD / 吨' },
  { mineral: '锌', market: 'LME 锌', price: '2,945.00', change: '+0.62%', unit: 'USD / 吨' },
  { mineral: '镍', market: 'LME 镍', price: '16,730.00', change: '+0.85%', unit: 'USD / 吨' },
  { mineral: '锂', market: '锂价格 · 市场待确认', price: '78,500.00', change: '+2.10%', unit: 'CNY / 吨' },
  { mineral: '铁矿石', market: '上海钢联铁矿石 · 示例', price: '785.00', change: '+0.38%', unit: 'CNY / 吨' },
]
export const navigation = [
  { id: 'overview', label: '情报总览', icon: '▦' },
  { id: 'news', label: '矿业新闻', icon: '▤' },
  { id: 'policy', label: '关键矿产政策', icon: '▧' },
  { id: 'prices', label: '市场价格', icon: '↗' },
  { id: 'ask', label: '智能问答', icon: '✧' },
  { id: 'pipeline', label: '数据管线', icon: '◎' },
  { id: 'eval', label: '质量评估', icon: '☷' },
]
export const sources = [
  { name: '矿业新闻', icon: '▤', status: '示例', providers: 'MINING.COM / S&P Global', description: '248 条文档　·　全文与结构化字段' },
  { name: '关键矿产政策', icon: '▧', status: '示例', providers: '中国稀土集团 / 澳洲 DISR', description: '200 条文档　·　政策条款与发布机构' },
  { name: '市场价格', icon: '↗', status: '待授权', providers: 'LME / SHFE / 上海钢联', description: '200 条记录　·　需核实接口与产品口径' },
]
