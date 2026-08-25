# `wechat-download-api` 原始需求与实现调研迁移矩阵

Last verified: 2026-08-25

Canonical index: [微信公众号智能聚合系统文档索引](../README.md)

## 迁移结论

`we-mp-rss` 继续作为唯一产品核心。旧 `wechat-download-api` 的需求与实现研究已迁移为本页的行为
矩阵、数据映射和安全不变量；没有迁移其 AGPL 源码、凭据、运行数据或仓库专属治理文档。

本页刻意区分“需求已进入核心文档”和“代码已经实现”。旧能力不能仅因出现在旧 README 中就被
写成当前核心的已完成功能。

## 证据快照

| 对象 | 快照 | 证据边界 |
| --- | --- | --- |
| 旧项目应用基线 | [`emohce/wechat-download-api@043c2f9`](https://github.com/emohce/wechat-download-api/tree/043c2f9828401220a00b7b125686b334581745e0) | 本地 `czz-main` 为 `3e85bab`，其中 3 个领先提交仅更新治理/知识文档；应用 README 与 `origin/main` 一致。 |
| 当前核心基线 | `rachelos/we-mp-rss` 的本地 `czz-main@fd666a7` | 已包含 v2 存储、后端、浮窗与 SupSub 文档提交；真实基础设施和外部服务仍未启用。 |
| 旧实现核验 | 旧 README、`vibe/knowledge/technical-details.md` 与聚焦源码地址 | 证明源码路径和静态行为；旧任务未运行真实扫码、轮询、导出或 MCP 客户端。 |

## 产品能力迁移

| 旧能力/需求 | 当前核心证据 | 决策状态 | 核心化要求与剩余缺口 |
| --- | --- | --- | --- |
| 公众号搜索、文章列表、公众号信息和关键词检索 | 现有微信驱动、订阅与文章查询；v2 提供工作区文章搜索 | `implemented-current` | 复用现有采集入口；任何 v2 投影继续执行工作区权限和共享来源预算。 |
| 扫码授权与授权失效通知 | [`jobs/failauth.py`](../../jobs/failauth.py) 和现有通知通道 | `implemented-current` | 保留通知能力；凭据只由现有授权系统或 secret reference 管理，不从旧仓库复制。旧项目“约 4 天、提前 24h/6h”只是旧实现策略，不写成平台保证。 |
| RSS/Atom/JSON/Markdown Feed | [`apis/rss.py`](../../apis/rss.py)、[`core/rss.py`](../../core/rss.py) | `implemented-current`（v1） | 保留现有 Feed；面向 Intelligence Hub 的工作区过滤、稳定游标和租户鉴权仍为 `planned`。 |
| 单篇文章下载 | [`apis/intelligence.py`](../../apis/intelligence.py)、[`core/intelligence/exporting.py`](../../core/intelligence/exporting.py) | `implemented-current`（v2） | 当前支持 MD/HTML/JSON/PDF/DOCX，并执行工作区校验。 |
| 整号/批量导出 | [`apis/tools.py`](../../apis/tools.py)、[`core/exporter.py`](../../core/exporter.py) | `partial-current` | 当前核心已有异步 ZIP 和 MD/DOCX/JSON/CSV/PDF；仍需日期/时间窗/增量范围、HTML/EPUB、统一用量与租户审计。旧项目的“只读本地库、不触发微信”必须成为导出不变量，当前图片/PDF 路径仍需专项核验。 |
| 本地 JSON 游标 + 单篇 Markdown 增量同步 | 现有 Feed 输出和 v2 单篇下载 | `partial-current` | 增加按发布时间与稳定次级键的工作区游标；空批次、重复时间戳和正文未就绪状态需要契约测试。 |
| MCP 搜索、订阅、最近文章和阅读工具 | 当前核心未发现 FastMCP、`/mcp` 或 MCP 配置入口 | `planned` | RAW-001 的 MCP 需求保留，但不能写成 v1 已存在。新实现必须使用当前用户/工作区权限或受限 Access Key；不继承旧项目的单用户静态 Token 与无鉴权 HTTP 边界。 |
| 图片代理与防盗链处理 | [`apis/proxy.py`](../../apis/proxy.py) 和现有图片 URL 重写 | `implemented-current` | 复用核心实现；继续采用 HTTPS、域名允许名单、响应大小/类型和重定向约束，不能扩成通用代理。 |
| Webhook/自定义投递 | 现有通知与消息任务；v2 durable outbox | `partial-current` | 现有通知继续使用；日报、授权失效和连接器投递逐步归并到可审计 outbox，外部写入按 R2 以上门禁执行。 |
| 分类、黑名单和深度历史抓取 | 现有标签/Feed 状态；v2 主题、来源状态和采集任务 | `partial-current` | 分类映射为标签/主题/工作区视图；失效来源进入带原因的采集状态。旧项目“验证 8 次自动拉黑”和 2–4 秒页间隔只作实现证据，不升级为通用平台规则。 |
| 多用户和外部访问 | 当前核心已有用户、Access Key 和 v2 工作区边界 | `implemented-current`（基础） | 旧项目无鉴权 HTTP、单账号多实例建议均被当前租户模型替代。RSS、导出、MCP 和公开链接逐项做权限收敛。 |
| 代理池、账户轮换和 TLS 指纹“规避风控” | 旧 README 的实现/营销描述 | `superseded` | 不作为目标、不写入自动降级；网络代理只能解决明确网络可达性，不能绕过验证码、额度或平台限制。 |
| SQLite-only 存储 | 旧项目 `rss.db` | `superseded` | SQLite 保留为 Lite；生产档位是 PostgreSQL + Redis，MQTT 仅用于 Distributed 事件，权威状态始终在数据库/outbox。 |
| 多个独立管理页面 | 旧项目静态 admin/RSS/history/categories/blacklist 页面 | `superseded` | 管理能力进入统一收件箱和右侧浮窗，不继续扩张主导航。 |

## 导出与本地读取不变量

1. Feed、摘要、单篇下载和批量导出默认只读取已经持久化并对当前工作区可见的文章；读取动作不得
   隐式触发微信列表、正文补采或付费供应商调用。
2. 需要远程图片内嵌的离线格式必须作为显式的“补全外部资源”模式，展示来源、网络请求预算、失败
   降级和缓存策略；不能把它伪装成本地只读。
3. 导出任务需要工作区、请求人、选择范围、格式、内容版本、结果对象、状态、用量和过期/清理策略；
   Redis/MQTT 不能成为任务或结果的唯一事实源。
4. 日期/增量导出使用 `publish_time + stable_id` 游标，避免相同发布时间漏项；分页完成后才推进游标。

## 数据迁移映射

| 旧 SQLite 语义 | 当前核心目标 | 迁移决定 |
| --- | --- | --- |
| `subscriptions` | 全局 `Feed`/公众号实体 + 工作区订阅关联 | 先只读扫描和去重预览；不直接复制旧主键。 |
| `articles` | 全局 `Article` + `int_workspace_articles` + 可选内容寻址 blob | 规范 URL、来源外部 ID 和内容证据联合去重；阅读/收藏/反馈不从全局状态继承。 |
| `categories` | 现有 Tags + v2 topics/工作区视图 | 名称冲突先预览；不自动覆盖用户主题。 |
| `blacklist` | 采集账户/来源状态、错误原因、冷却与禁用状态 | 迁移为可解释状态，不创建永久且无原因的全局拉黑。 |
| `source=poll\|deep_fetch` | `ingestion_source`、provider identity、采集任务和游标 | 保留来源血缘；不把旧状态值当成当前任务成功收据。 |
| `UNIQUE(fakeid, link)` | provider 外部身份 + 规范 URL/内容去重 | `fakeid` 失效时仍能依据内容证据识别重复。 |
| token、cookie、代理和 webhook | secret reference / 当前授权与通知配置 | 永不迁移明文；需要用户重新授权或配置。 |

实际读取旧 SQLite、生成数据迁移计划、执行 DDL/DML 或回填仍是独立数据库门禁。本次仅同步映射，
没有连接或修改任何旧数据库。

## 许可证与文档边界

- `wechat-download-api` 为 AGPL-3.0-only。当前核心只采用需求、行为描述、数据映射和经独立核验的
  设计原则，不复制旧实现函数、模板、静态资源或生成文件。
- 旧仓库的 `AGENTS.md`、`vibe/rules/`、`vibe/specs/` 和知识索引继续留在旧仓库作为来源治理记录；
  核心仓库使用自己的 `AGENTS.md` 和
  [Controlled 任务](../tasks/260824-wechat-intelligence-hub/spec.md)，因此不做物理复制。
- 采集限频、付费 API 和其他开源路线的综合结论由
  [采集路线与开源边界](../research/wechat-collection-landscape.md)持有；本页不重复易变价格或额度。

## 当前完整性判断

- 原始需求、旧行为清单、实现研究、数据映射、许可证边界和否决项：`synchronized`。
- 当前核心代码状态：按上表分别为已实现、部分实现或计划；不能整体宣称“旧项目功能已全部实现”。
- 凭据、运行数据、真实微信/付费调用、数据库迁移、MCP、租户化 Feed 和批量导出补齐：`not executed`。
