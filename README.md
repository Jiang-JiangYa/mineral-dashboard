# 矿观 · 矿业三源情报系统

Vue 3 + FastAPI + SQLite/sqlite-vec。支持公开网页采集、授权行情导入、清洗去重、持久化向量检索、带引用的中文问答、采集状态与20条参考问答评估。

**代码链路可本地跑通，但当前不满足“近30天三类各200条”的数据验收。** 实际访问发现：MINING.COM 403，DISR 本机连接超时，中国稀土官网当前栏目文档较旧；S&P RSS 和行情授权接口尚未提供。界面显示实际数量，不用模拟数据补齐。碳酸锂期货属于 GFEX，题目的“SHFE 锂”需确认。

## 一键启动（Windows PowerShell）

环境：Python 3.12 64位（建议）、Node.js 24。进入项目目录，不在父目录运行 npm。

```powershell
cd D:\iwen_codex\FDE_yj\mineral-dashboard
npm run setup
npm start
```

- 首次 setup 安装 Python/npm 依赖，复制 `.env.example` 为本地 `.env`，初始化数据库及10个历史政策章节摘要，运行20条评估并构建网页。需要联网安装依赖。
- 后续直接 `npm start`，它重新构建前端并启动 FastAPI。
- 网页：[http://127.0.0.1:8000](http://127.0.0.1:8000)
- 交互 API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Ctrl+C 停止服务；数据保存在 `data/`，重启不丢失。
- 已有服务占用8000时先停止旧进程；或使用 uvicorn 的 `--port 8001`，同源网页打开对应端口。

本机本次已完成依赖安装与初始化，可直接 `npm start`。默认使用不需模型下载/密钥的哈希向量检索基线和抽取式回答；语义模型选项见后文。

## 开发方式

两个终端，均在项目根目录：

```powershell
# 终端1：后端
npm run backend
# 终端2：Vue 热更新（/api 自动代理到8000）
npm run dev
```

开发网页 http://127.0.0.1:5173。问答设置留空时调用本项目 `/api/query`；保留了此前自定义接口地址的 localStorage 兼容，旧地址失效时到「接口设置」清空保存。

Linux/macOS 可手动执行 `python3 -m venv .venv`、激活环境、`pip install -r requirements.txt`、`npm ci`、`python -m pipeline bootstrap`、`python -m eval.run`、`npm run build`、`uvicorn serve.app:app --host 127.0.0.1 --port 8000`。Windows 一键脚本和当前锁文件在本机 Python3.12/Windows64位验证。

## 采集与导入

```powershell
# 所有已配置来源，默认近30天、每类适配器目标200条、最多250页
npm run collect
# 单独公开源，控制预算
.venv/Scripts/python.exe -m pipeline collect --sources mining regcc disr --days 30 --limit 200 --max-pages 250
# 实际数量与缺口
.venv/Scripts/python.exe -m pipeline status
# 重复执行安全：同主键更新，相同内容不重复计数
.venv/Scripts/python.exe -m pipeline bootstrap
# 标准化文档 JSONL
.venv/Scripts/python.exe -m pipeline import-jsonl D:/authorized/documents.jsonl
# 已获授权行情 CSV/JSON
.venv/Scripts/python.exe -m pipeline import-prices D:/authorized/prices.csv --source LME --url https://www.lme.com/
```

网页「数据管线 → 启动采集」也可启动后台作业；运行时自动刷新，详情可查看来源错误、排除与新增计数。进程退出会中断作业，不是持久任务队列。价格序列按来源、市场、产品、合约、口径、币种和单位分组，绝不使用公式生成假趋势。

`.env` 配置：

| 变量 | 用途 |
| --- | --- |
| MINING_RSS_URLS | MINING.COM RSS，可逗号分隔多个已确认订阅地址 |
| SPGLOBAL_RSS_URLS | 题目未提供实际 S&P RSS，需填真实地址 |
| DISR_URLS / REGCC_URLS | 政策入口，默认已配置公开网站 |
| LME_DATA_URL / MYSTEEL_DATA_URL | 已授权、已标准化的 CSV/JSON 行情接口 |
| LME_AUTH_HEADERS / MYSTEEL_AUTH_HEADERS | JSON格式请求头，仅保存在本地 |
| GFEX_DATA_URL / GFEX_AUTH_HEADERS | 可选GFEX行情，不能默认为SHFE源达标 |
| DATA_DIR | 数据目录，默认data/ |
| REQUEST_INTERVAL / REQUEST_TIMEOUT / HTTP_RETRIES | 频控、超时、有限重试 |

行情模板见 `config/prices.example.csv`（仅表头）；必须含时间时区、市场、品种、报价口径、币种、单位和精确金额。当前连接器要求标准字段；具体供应商私有接口需要按其文档完成字段转换，不猜测单位或绕过登录。完整 schema 与去重规则见 [DATA_NOTES.md](DATA_NOTES.md)。

## REST 接口

```powershell
$body = @{ question = '近 7 天澳洲锂出口政策有何变化？'; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/query -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

可先问「澳大利亚关键矿产战略对本国加工能力有何目标？」验证参考资料问答。带近7天的查询不会拿2023年历史摘要冒充近期政策；无证据会明确拒答。

请求支持 `filters: {kind, minerals:[], countries:[], since, until}`，日期用 ISO8601 带时区；`as_of` 可固定相对时间解释时点。响应包含 `answer`、`sources`（文档ID/URL/标题/日期/原文片段/参考标记）、`claims`、`filters`、`abstained`、`method`、`encoder`。

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | /query、/api/query | 自然语言检索问答 |
| GET | /api/health | 健康检查 |
| GET | /api/overview | 真实数量、缺口、来源、评估、作业状态 |
| GET | /api/documents?kind=policy&limit=100&offset=0 | 分页文档 |
| GET | /api/documents/{id} | 单文档详情 |
| GET | /api/prices | 最近最多1000条行情 |
| GET | /api/sources、/api/runs | 来源配置状态、采集报告 |
| POST | /api/collect | 启动采集，可指定sources/days/limit/max_pages |
| GET / POST | /api/eval | 读取 / 执行20条参考评估 |

本地默认仅监听127.0.0.1。管理操作无令牌时仅允许本机；设置 `MANAGEMENT_TOKEN` 后 POST采集/评估需要 `Authorization: Bearer ...`，网页不保存密钥，可用CLI或API文档操作。需要网络部署时显式配置 `ALLOWED_HOSTS`、`CORS_ORIGINS` 和访问控制。

## 向量模型与回答方式

默认 `EMBEDDING_BACKEND=hash`：确定性的中英别名/词项特征哈希向量，sqlite-vec余弦距离结合词项覆盖排序。它是离线检索基线，**不是预训练语义模型**；对复杂同义改写能力有限。

可选多语语义模型（首次联网下载，可能较大）：

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-semantic.txt
```

在 `.env` 设置：

```dotenv
EMBEDDING_BACKEND=sentence-transformers
EMBEDDING_MODEL=intfloat/multilingual-e5-small
DATA_DIR=data-semantic
```

使用新目录重新 bootstrap/采集/导入，再运行评估。旧库编码器签名不同会拒绝启动，避免混用。`data-*/` 已排除；使用其他自定义数据目录时需自行添加Git忽略规则。默认回答直接抽取来源片段并引用，不调用付费LLM，也不在缺证据时生成事实。

## 自动评估和测试

```powershell
npm test
npm run test:backend
npm run evaluate
npm run build
```

- `eval/ground_truth.json`：20条中文标准问答、预期事实、原始URL。
- `eval/corpus.py`：DISR历史战略10个章节的中文人工摘要，明确标为reference，不计入近期采集。
- `eval/run.py`：同线上检索链路跑Recall@5、标准答案短语命中率、回答忠实度，报告写入 `data/eval/latest.json`。
- 忠实度采用抽取断言的原文精确支持率；不是独立LLM裁判。小参考集高分不能证明近期三源效果。详见数据说明。
- 测试数据仅在临时目录/前端mock中，绝不导入正式数据库充数。

## 目录

```text
pipeline/        模型、HTTP/RSS/HTML/行情采集、清洗、去重、向量化、SQLite、CLI
serve/           FastAPI、自然语言过滤、混合检索、引用回答
eval/           20条金标准、历史参考摘要、自动评估
src/             Vue3页面与真实API联调
scripts/         Windows初始化/启动
config/          行情标准字段模板
tests/           前端与后端回归测试
DATA_NOTES.md    schema、主键、去重、来源限制、评估口径
.env.example     可分享配置，无账号密钥
```

`data/`、`.venv/`、`node_modules/`、`dist/`、`.env`、日志和本地AGENTS.md不入Git。保留原Gitee仓库、历史与 `.openai/hosting.json`；本次不自动推送或更新线上站点。

现有 Sites 是静态托管，不能直接运行Python服务。完整系统当前在本机8000端口提供；若上线，需要另行部署FastAPI及持久磁盘，并为前端配置可访问的HTTPS后端。
