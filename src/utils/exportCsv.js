export function createDocumentsCsv(records) {
  const rows = records.map(record => [record.type, record.mineral, record.title, record.source, record.date, record.is_reference ? '历史参考摘要' : '采集记录', record.url || ''])
  const escape = value => `"${String(value ?? '').replace(/^[=+@-]/, "'$&").replaceAll('"', '""')}"`
  return '\ufeff' + ['类型,矿种,标题,来源,日期,数据性质,原始链接', ...rows.map(row => row.map(escape).join(','))].join('\r\n')
}
export function exportDocuments(records) {
  const blob = new Blob([createDocumentsCsv(records)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '矿观-情报导出.csv'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
