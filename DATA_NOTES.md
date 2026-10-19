# 数据说明

## 验收口径与当前状态

- “条”按原始新闻、原始政策文件或价格观测记录计数，不按向量切片计数。
- 近 30 天是运行时 UTC 当前时间向前滚动 30×24 小时；各类分别至少 200 条，总计至少 600 条。
- 当前按新闻、政策、价格三类验收；若题目要求每个网站各 200 条，需要另设网站级验收。
- `python -m pipeline status` / `/api/overview.coverage` 为实时结果，`passed` 必须三类均达标才为 true。
- 首次实采未达标：MINING.COM 的 robots 请求返回 403；DISR 在本机网络 TLS 连接超时；中国稀土集团官网可访问，但当前行业动态和公告栏目未发现本次窗口内合格政策；S&P RSS 未提供，价格接口未授权。
- 这是实际访问结果，不是永久判定。重跑后以数据库作业报告为准；不能用改日期、切片、重复报价或模拟记录补足数量。
- 参考库是 DISR 2023 战略的 **10 个章节中文人工摘要**，不是 10 份近期政策全文。`is_reference=true`，不计入近 30 天统计。日期为该战略官网注明的 2023-07-07 修订版本日期。
- 题目的“SHFE 锂”有交易所口径问题：碳酸锂期货属于 GFEX。GFEX 适配为可选项，不能作为已满足 SHFE 指定源的证明。参见 [广期所合约公告](https://www.gfex.com.cn/gfex/sytslqhhy/202307/9ad927b8ec4c458594e172fd1ada2a9b.shtml)。

## 目录和持久化

`DATA_DIR` 默认 `data/`，相对路径按项目根目录解析，整体不入 Git。

本地保留数据目录时可跨进程重启保存数据；当前Render免费演示使用 `/app/data` 临时目录，没有持久盘，休眠、重启或重新部署会丢失运行期间写入的数据。首次空库重新初始化的历史参考不代表恢复了此前的采集数据。长期保存需另配持久化存储，详见 [部署说明](DEPLOYMENT.md)。

| 文件 | 内容 |
| --- | --- |
| `data/mineral.sqlite3` | 文档、切片、向量、编码器元信息和采集运行记录 |
| `data/raw/*.raw` | 响应原始字节，按内容 SHA-256 命名，不包含授权请求头 |
| `data/pipeline.lock` | 采集作业互斥锁，避免 CLI/API 重复触发 |
| `data/eval/latest.json` | 最近评估、逐题结果、基准哈希和编码器版本 |

SQLite 启用 WAL 和外键。每次连接加载 sqlite-vec；文档更新、旧切片/向量删除、新切片/向量写入在一个事务中完成。建议仅本地单服务进程运行，不把此实现作为多机任务队列。

## Record schema

所有输入通过 `pipeline/models.py::Record` 校验。JSONL 每行一个对象。接口公开记录增加 `id`、`date`、`mineral`、`category`，隐藏本地 `raw_path`；前端映射 `kind → type`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `kind` | news / policy / price | 来源类别 |
| `source` | string | 来源名称，必须保留真实身份 |
| `url` | HTTP(S) string | 原文或行情来源链接，禁止嵌入用户名密码 |
| `title` | string | 标题，3–1000 字符 |
| `text` | string | 清洗后正文/行情观测说明，20–300000 字符 |
| `published_at` | ISO 8601 datetime | 原文发布日期或行情观测时间，禁止未来时间 |
| `fetched_at` | ISO 8601 datetime | 获取时间，不能替代发布日期 |
| `minerals` | string[] | 铜、锌、镍、锂、铁矿石、稀土、钴、金、石墨等标签 |
| `countries` | string[] | AU/CN/US/CA/CL/ID 等代码 |
| `publisher` | string | 发布机构（可空） |
| `document_type` | string | web_article / price_observation / translated_reference_summary 等 |
| `is_reference` | bool | 是否为历史参考，默认 false |
| `market` | string | 价格必填，如 LME、GFEX；不自动换市场 |
| `instrument` | string | 价格必填，产品名称 |
| `contract` | string | 合约或期限（现货可空） |
| `quote_type` | string | 价格必填，结算/收盘/cash/3M 等实际口径 |
| `currency` | string | 价格必填，如 USD/CNY |
| `unit` | string | 价格必填，如 tonne/吨；不隐式换算 |
| `price` | Decimal | 有限正数，JSON 中用十进制字符串保存精度 |
| `raw_path` | string | 原始响应在 DATA_DIR 内的相对路径（可空） |

采集日期优先级：文章发布 meta → JSON-LD datePublished → 带标签的页面发布日期 → RSS 日期。**不使用采集时间填补缺失日期。** 无时区的中国稀土页面按 UTC+8，其他网页按 UTC 解释；标准化行情输入强制包含时区。手动 JSONL 无时区日期按 UTC，建议显式带时区。

正文去掉脚本、导航、页脚、广告等，Unicode NFKC 和空白规范化。公开网页正文不足 200 字符时拒收，可能遗漏短公告，需要人工复核。政策标题必须有政策/战略/条例/通知等标志且内容涉及矿种；它是保守规则分类，不等于法律效力判断。国家和矿种标签是字典匹配，可能漏标或误标，允许导入时明确提供。

## 表结构与主键

| 表 | 关键字段 |
| --- | --- |
| `documents` | id PK, kind, source, url, title, text, published_at, fetched_at, content_hash, is_reference, payload JSON |
| `chunks` | id PK, document_id FK, position, text |
| `vectors` | sqlite-vec vec0：id PK，与 chunks.id 对应；embedding float[dimension] |
| `runs` | id UUID PK, started_at, finished_at, status, report JSON |
| `meta` | key PK, value；保存编码器 signature，禁止混用模型 |

- 新闻/政策 ID = SHA256(`source + canonical_url`)。
- 价格 ID = SHA256(`source + market + instrument + contract + published_at + quote_type + currency + unit`)。金额更正更新同一观测，非新增观测。
- URL 规范化：scheme/host 小写，去 fragment、末尾 `/` 和 utm_/fbclid/gclid/ref 跟踪参数，其余 query 排序保留。
- 正文 content_hash = SHA256(清洗文本)。新闻/政策同类同正文不同 URL 返回 `duplicate`，不新增。当前不保留多来源转载别名表，返回首次记录，不能声称所有转载出处均保留。
- 相同主键且字段（除 fetched_at）不变返回 `unchanged`；正文、标题、标签或参考状态更正返回 `updated`，同步替换旧向量。重复运行不增加原始计数。
- 切片默认 900 字符、120 重叠，优先按换行或句号断开；切片 ID = SHA256(`document_id:position`)。
- **未实现语义近重复去重**：改写稿、不同语言转载或正文有细微差别可能仍算独立记录，需要人工核查。

## 采集与授权接口

- 公开网页尊重 robots；robots 404/410 表示无文件，403/网络错误不继续访问；没有验证码或付费墙绕过。
- 默认每域至少间隔 1 秒，15 秒超时，对 429、5xx 和网络异常有限重试；重试退避有上限。
- RSS 跟随 rel=next；识别 WordPress generator 时采用其 paged 分页；HTML 只发现同域矿产相关文章与下一页，受 `max_pages` 和 `limit` 约束。未发现下一页时如实报告不足，不能保证 RSS 提供足够历史。
- 不从列表标题推断全文，不拿公司党建/招聘公告冒充矿产政策；缺少发布日期、过旧、过短或分类不符记录在排除计数中。
- 当前行情连接器接受**已标准化**的 CSV/JSON，并非对所有供应商私有 schema 的通用猜测器。需要用户提供合法接口与字段映射；拿到接口文档后可在 `price_records` 前增加供应商转换层。
- CSV/JSON required：`published_at,market,instrument,quote_type,currency,unit,price`；optional：`contract,url`。CSV 模板 `config/prices.example.csv` 只有表头，无模拟报价。
- JSON 为数组，或 `{"items":[...]}` / `{"data":[...]}`。行情各行先全部校验再写入；JSONL 也先整体校验，但数据库写入故障可能使已完成事务保留，重跑可幂等恢复。
- `LME_AUTH_HEADERS` 等只从本地 `.env` 读取，使用 JSON 对象配置 Authorization 等字段；不要在 URL 参数中放令牌。未配置返回 `needs_configuration`。
- CLI/API 作业详情保存在 `runs`，可定位各源网络错误。后台线程只在当前服务进程存活时运行；服务中断后需重新发起作业。

## 检索与回答

默认离线 `hash-blake2b-alias-v1:384`：英文词、中文二元词和中英矿种/国家别名构成特征哈希向量，配合词项覆盖分数。这是可复现基线，**不是预训练语义模型**。sqlite-vec 真实保存并计算向量距离。

可选 `sentence-transformers` + `intfloat/multilingual-e5-small` 使用归一化语义 embedding，区分 query:/passage: 前缀。首次需下载模型。切换后使用新 DATA_DIR 并重新导入/采集；签名不一致会拒绝启动。

日期、国家、矿种、类型先做 SQL 过滤，再计算候选切片 cosine 距离 + 词项覆盖，按文档合并前 k 个结果。当前过滤后向量距离为精确扫描，适合小规模本地数据，非大规模 ANN 集群。

中文时间支持近 N 天、近七天/近一周、今天、昨天、本月，按上海时区解释；没有时间词不添加近期限制。显式 filters 覆盖推断；未知复杂自然语言可能无法解析，可显式传参。无满足条件的证据时返回 `abstained=true`，不放宽过滤，也不推断“政策没有变化”。

默认回答是**抽取式**：返回原文证据、发布日期、引用编号和可点击来源。历史摘要会标注参考身份；不是自动生成法律分析，也不做没有前后版本证据的变化断言。不依赖 LLM API Key。

## 评估说明

- `eval/ground_truth.json` 冻结 20 条中文 Q&A、gold_urls；`eval/corpus.py` 是对应历史章节中文摘要和可追溯官网链接。
- `python -m eval.run` 按线上相同 query 函数检索，recall@5 = 前五个文档覆盖 gold IDs 比例，按题平均。
- answer faithfulness = 抽取断言在其引用片段中精确出现的比例。无证据拒答为 null，不把拒答计为 100%；另报标准答案短语命中率。
- 该指标验证引用没有脱离原文，不是独立 LLM/人工语义判分；在抽取式系统上天然较高。小参考集高分不证明近期三源回答质量。
- 替换真实业务基准时应扩充新闻/价格、多文档问题与无答案问题，人工核验金标准，冻结独立于检索逻辑的标注，再报告泛化指标。
