# 公开部署方案

## 当前状态

**2026-10-19 已完成 Render 免费服务部署。** 公开地址：[矿观系统](https://mineral-dashboard-lss6.onrender.com/)。Render部署记录显示 `Deploy succeeded | Live`，应用启动完成且首页GET返回200；镜像由Render构建，本地未做Docker构建验证。

已上线的应用代码提交为 `50732bb`；后续文档提交不等于应用已重新部署。线上完整场景验收尚需按下方清单逐项记录，不能仅凭部署成功判断全部业务功能达标。

现有 Sites 仅托管旧静态网页，无法原样运行 FastAPI、sqlite-vec 和本地数据库。新方案把 Vue 构建结果和 Python API 放进同一个 Docker 服务，网页和 `/api` 同源。

## 当前选择：Render 免费演示

用户已选择先使用免费方案。根目录 `render.yaml` 现为 `plan: free`，不挂付费磁盘；前后端仍在同一服务内，空库启动恢复10条历史参考摘要。采集/导入的新数据会在休眠、重启或部署后丢失。模板中的管理令牌仍保留，不能用空密钥公开管理接口。

## 可选付费升级：Render 托管 Web Service + 持久磁盘

适合当前少量访客分享演示，保留现有 Python/SQLite 架构：

| 配置 | 选择 |
| --- | --- |
| 运行方式 | Docker，根目录 Dockerfile |
| 地区 | Singapore；实际访问体验上线后验证 |
| 计算规格 | 0.5c-512mb（512 MB），单实例 |
| 存储 | 1 GB 持久磁盘，挂载 `/app/data` |
| 网页 | 平台生成的 `*.onrender.com` HTTPS 地址，无需先买域名 |
| 健康检查 | `/api/health` |
| 启动命令 | 保留 Dockerfile CMD：`python -m serve` |
| 管理保护 | MANAGEMENT_TOKEN，由平台生成，不交给普通访客 |

2026-10-19 查询官方定价：计算资源 $7/月，磁盘 $0.25/GB/月，因此上述基础约 $7.25/月；超额流量、构建用量、税费等另计，以创建页账单为准。不是固定总价承诺。

- [Render 定价](https://render.com/pricing?trk=article-ssr-frontend-pulse_little-text-block)
- [持久磁盘](https://render.com/docs/disks)：免费Web Service不能挂载；没有磁盘时重启/部署会丢本地数据。
- [公开 Web Service 与默认 HTTPS 域名](https://render.com/docs/web-services)

默认 hash 编码器适合先做小数据演示。若改为本地多语模型，需要重新评估内存规格与费用，不能把512MB视为模型运行保证。

## GitHub 代码接入与更新

当前部署源码：[GitHub仓库](https://github.com/Jiang-JiangYa/mineral-dashboard)。本地远程 `github` 指向该地址，原 `origin` 保留Gitee；向一个远程推送不会自动同步另一个远程。

1. 在Render通过GitHub连接选择该仓库及 `main` 分支，运行方式选择Docker，套餐选择Free。此前表单拒绝了Gitee地址，不再将直接填写Gitee URL作为本项目已验证路线。
2. 更新时先检查变更并提交，再执行 `git push github main`。
3. 需要更新运行中的应用时，在Render选择 `Manual Deploy → Deploy latest commit`，核对部署提交及日志。模板关闭自动部署，实际以服务后台设置为准。参见[官方部署说明](https://render.com/docs/deploys)。
4. 仅修改Markdown文档通常无需重新部署应用；GitHub上的文档会随推送更新。

`render.yaml` 默认免费、不挂磁盘。只有用户以后明确选择付费升级时，才将plan改为相应付费规格并添加1GB磁盘；上表仅供付费升级参考。

## 平台环境变量

- `DEPLOYMENT_MODE=public`
- `DATA_DIR=/app/data`：免费环境为临时目录；未来挂持久盘时应与挂载路径一致。
- `EMBEDDING_BACKEND=hash`
- `BOOTSTRAP_REFERENCE=1`：仅空库初始化10个历史参考摘要和评估，已有数据库不覆盖。
- `MANAGEMENT_TOKEN`：至少32字符的随机密钥，妥善保存，不写到前端或Git。Blueprint模板可自动生成；手动创建服务时需在Environment中添加。
- `PORT`：使用Render注入的端口。
- Render自动提供 `RENDER_EXTERNAL_HOSTNAME`，入口会据此设置默认Host白名单和HTTPS Origin；绑定自有域名时显式补充 `ALLOWED_HOSTS` 和 `CORS_ORIGINS`。

普通访客可查看已入库数据和提问；采集、运行评估仍需管理员令牌。公开部署会公开数据库中的文档与报告，导入授权行情前先确认它允许对外展示。

手动配置密钥：在本地运行 `python -c "import secrets; print(secrets.token_hex(32))"`，将输出保存到Render服务的 `Environment → Add Environment Variable`，Key填 `MANAGEMENT_TOKEN`，Value填生成值，保存并重新部署。不要把密钥贴到聊天或截图中。首次部署曾因缺少该变量失败，补充后启动成功。

## 备选：已有云服务器时使用 Docker Compose

当前无服务器时不需要购买或配置这条路线；文件保留供以后迁移。

```shell
cp .env.deploy.example .env.deploy
# 修改域名，并在本机生成随机 MANAGEMENT_TOKEN 填入文件
docker compose --env-file .env.deploy --profile https up -d --build
docker compose --env-file .env.deploy logs --tail=100 app
```

需要服务器已安装Docker/Compose、域名解析到服务器、80/443可访问。Caddy提供HTTPS反向代理；FastAPI的8000端口默认仅绑定服务器回环地址。数据库使用命名卷，更新容器时保留；不要执行 `down -v`，这会删除卷。证书与数据库都应备份。

## 上线验收

1. 平台构建成功，健康检查通过，打开实际HTTPS地址。
2. `/api/health` 返回ok；历史战略问题有来源引用，近期无证据问题拒答。
3. 无令牌POST `/api/collect` 与 `/api/eval` 被拒绝。
4. 免费环境确认空库初始化及数据重置行为，提前备份有价值的数据；只有升级持久盘后，才验收重启/重部署后新增文档与评估仍保留。
5. 用另一台设备或无登录浏览器访问，确认访客能正常浏览。
6. 核对资源与用量账单；网站公开不等于题目的600条真实数据验收达标。

## 免费体验的区别

当前就是免费演示实例，不是持久化上线：15分钟无访问会休眠，唤醒约一分钟；运行期间写入的SQLite等本地文件在休眠、重启或重新部署后丢失。每工作空间每月750个免费实例小时，另有流量与构建额度；规则及超额处理以[官方免费服务说明](https://render.com/docs/free)为准。没有固定30天到期限制的是免费Web Service；免费PostgreSQL的30天到期规则是另一项产品限制，本项目未使用它。

若需要保留真实采集结果，应另行选择持久化存储方案；当前不自动升级或产生付费配置。
