# 公开部署方案

## 当前状态

部署文件已经准备好，**尚未创建线上服务、没有付费、没有生成新的公开完整系统地址**。本机目前未安装 Docker，容器镜像尚未实际构建；部署前必须以平台构建和运行结果验证，不能把文件准备完成当成部署成功。

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

## Gitee 代码接入

部署前需提交最新文件，并确认平台拉取的是最新commit。用户已指定将本项目同步到GitHub仓库 `https://github.com/Jiang-JiangYa/mineral-dashboard.git`，保留原Gitee远程。

Render可连接Git提供商仓库或公开Git URL。当前项目是Gitee：

1. 若仓库可匿名克隆，可在 Web Service 的 Public Git Repository 中尝试填入现有地址；Render侧是否能正常拉取须实际验证。
2. 公开URL方式通常不支持自动部署；后续更新手动触发。参见[官方部署说明](https://render.com/docs/deploys)。
3. 如Gitee仓库私有或平台拉取失败，可经用户授权镜像到其GitHub/GitLab仓库，再连接部署；不要自动创建新远程或公开私有代码。

`render.yaml` 默认免费、不挂磁盘。只有用户以后明确选择付费升级时，才将plan改为相应付费规格并添加1GB磁盘；上表仅供付费升级参考。

## 平台环境变量

- `DEPLOYMENT_MODE=public`
- `DATA_DIR=/app/data`，与持久盘挂载路径一致。
- `EMBEDDING_BACKEND=hash`
- `BOOTSTRAP_REFERENCE=1`：仅空库初始化10个历史参考摘要和评估，已有数据库不覆盖。
- `MANAGEMENT_TOKEN`：至少32字符，平台生成并妥善保存，不写到前端或Git。
- `PORT`：使用Render注入的端口。
- Render自动提供 `RENDER_EXTERNAL_HOSTNAME`，入口会据此设置默认Host白名单和HTTPS Origin；绑定自有域名时显式补充 `ALLOWED_HOSTS` 和 `CORS_ORIGINS`。

普通访客可查看已入库数据和提问；采集、运行评估仍需管理员令牌。公开部署会公开数据库中的文档与报告，导入授权行情前先确认它允许对外展示。

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
4. 重启/重部署后文档数和评估仍保留，确认持久盘实际可写。
5. 用另一台设备或无登录浏览器访问，确认访客能正常浏览。
6. 核对资源与用量账单；网站公开不等于题目的600条真实数据验收达标。

## 免费体验的区别

Render免费服务不能挂持久盘，空闲会休眠，重启后的SQLite数据会丢失。若只想短期试看，可以单独创建免费临时演示实例并明确接受这些限制，但不能把它称为已完成持久化上线。当前render.yaml已经采用免费配置；需要持久化时必须另行确认付费升级。
