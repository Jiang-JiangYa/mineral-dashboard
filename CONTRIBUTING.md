# 开发与工程约定

## 目录边界

本项目是同仓库管理的前后端应用，保留题目要求的 `pipeline/`、`serve/`、`eval/`：

- `src/`：Vue 组件、页面状态与浏览器请求；不用静态演示数据替代真实错误。
- `serve/schemas.py`：HTTP 请求校验；`serve/app.py`：应用工厂、路由和服务配置；`serve/retrieval.py`：检索与引用回答。
- `pipeline/`：采集、清洗、去重、向量化及持久化，不依赖 Vue 或浏览器运行时。
- `eval/`：固定基准、参考摘要、指标与报告；它与真实采集数量分别统计。
- `tests/backend/` 和 `tests/dashboard.test.js`：隔离测试，禁止向真实数据库写入测试记录。
- `scripts/`：工程命令；不在源码里硬编码开发者机器的绝对路径。

当前规模不强制引入 Router、Pinia、Docker 或拆成多个仓库；新增复杂度必须有具体需求。

## 初始化与开发

Node.js 24、Python 3.12 64位为本项目验证环境。Windows 执行 `npm run setup`，该命令安装运行与开发依赖；其他系统按 README 创建 `.venv`，然后执行：

```shell
python -m pip install -r requirements-dev.txt
npm ci
```

`requirements.txt` 声明直接运行依赖，`requirements-lock.txt` 固定已验证的运行依赖版本；测试和 Ruff 只在 `requirements-dev.txt` 中。前端依赖版本以 `package-lock.json` 锁定。依赖变更必须同步锁文件，不手写猜测其内容。

`npm run backend`、`npm run test:backend` 等通过 `scripts/python.mjs` 选择 Windows/Linux/macOS 对应的项目虚拟环境，不使用系统 Python 回退。后端统一以 `serve.app:create_app --factory` 启动，普通 import 不创建数据库。

## 检查与格式

```shell
npm run check                 # 顺序执行全部检查，失败立即停止
npm run lint                  # ESLint：JS/Vue错误
npm run format:check          # Prettier：前端格式
npm run lint:backend          # Ruff：Python错误和导入顺序
npm run format:backend:check  # Ruff：Python格式
npm test                      # 前端回归
npm run test:backend          # 后端回归
npm run build                 # 前端生产构建
```

自动修正格式：`npm run format`、`npm run format:backend`。格式检查不修改文件。`.editorconfig` 约定缩进、编码与末尾换行，`.gitattributes` 统一 Git 换行；PowerShell 保留 UTF-8 BOM 和 CRLF，供 Windows PowerShell 正确读取中文。

CI 可使用 Node24/Python3.12，安装上述开发依赖后运行 `npm run check`，无需启动外部数据库或访问新闻源。本仓库托管在 Gitee，目前没有配置远端自动流水线，不能把本地脚本描述成已启用云端 CI。

## 配置、数据与报告

- 密钥只放本地 `.env`，示例仅写占位值。不要输出授权请求头。
- `Settings` 必须先验证超时、间隔、重试次数；创建数据库属于 Store/应用启动职责，不属于模块导入职责。
- 原始数据和本地数据库必须排除；`src/data/` 导航源码必须跟踪。
- 评估报告使用唯一临时文件和原子替换，API与CLI同时评估不会争用同一个 `latest.tmp`。
- 修改行为要加有意义的回归，测试使用临时目录；调整格式不需要编写镜像式测试。
- 对源访问失败、行情未授权、数据量不足和评估局限如实说明。实采或评估快照以日期标注，不冒充当前状态。

## 提交前

执行 `npm run check`，再检查 `git diff --check`、`git status` 和暂存清单。禁止提交 `AGENTS.md`、`.env`、数据库、`data/`、缓存、依赖目录或构建产物；不要用 `git add -f` 绕过规则。提交、推送和部署分别按用户授权进行。
