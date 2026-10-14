# 矿观 · Vue 3 情报工作台

使用 Vue 3 Composition API、单文件组件和 Vite。保留原版布局、筛选、情报详情、示例价格走势图、CSV 导出和问答接口设置。

## 启动与构建

使用 Node.js 22.12+（推荐 Node.js 24 LTS；也支持 Node.js 20.19+）。系统旧版 Node.js 18 不支持本项目的 Vite 版本。

```sh
npm ci
npm run dev
npm test
npm run build
npm run preview
```

开发服务默认显示 `http://127.0.0.1:5173`。构建产物生成到 `dist/`，由 Sites 静态托管。该目录不再存放手写源码，也不纳入 Git；部署前需要构建。

## 目录

- `src/App.vue`：布局、页面切换与共享筛选状态。当前保留原版单页切换行为，无需路由或全局状态库。
- `src/components/`：侧栏、问答、统计、新闻列表、价格图表、来源面板、详情视图与设置弹窗。
- `src/composables/useQuery.js`：问答请求、加载状态、20 秒超时和卸载取消。
- `src/data/demo.js`：明确标注的演示文档与价格；未接入真实采集管线。
- `src/assets/main.css`：原有视觉样式及响应式布局。
- `src/utils/exportCsv.js`：UTF-8 BOM CSV 导出及字段转义。
- `tests/`：交互回归与接口成功、错误、超时场景。
- `.openai/hosting.json`：沿用现有私有 Sites 标识与 `dist` 发布目录。

## 问答接口

在侧栏「接口设置」中填写完整 `/query` URL，设置保存在浏览器 `localStorage` 的 `mineral-query-endpoint`，兼容旧版设置；留空使用演示回答。接口须允许网页来源跨域访问，HTTPS 网页应配置 HTTPS 接口。

```http
POST /query
Content-Type: application/json

{"question":"近 7 天澳洲锂出口政策有何变化？"}
```

响应最少包含 `{"answer":"回答文本"}`。回答通过 Vue 文本插值显示，不执行服务返回的 HTML。

新闻、政策、价格与评估指标均为演示，Vue 迁移不包含采集后端或向量库。
