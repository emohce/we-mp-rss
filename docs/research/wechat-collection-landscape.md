# 微信公众号采集路线与开源边界

Last verified: 2026-08-24

## 结论与证据等级

- **源码确认**：`we-mp-rss` 使用已登录公众号后台的 token、cookie、`faker_id`，请求
  `appmsgpublish`/`appmsg` 类列表接口并按 `begin/count` 翻页；`200013` 和 `200003` 已在上游
  代码中作为不同错误处理。参见
  [`core/wx/model/app.py`](../../core/wx/model/app.py) 与
  [`core/wx/model/free_publish.py`](../../core/wx/model/free_publish.py)。
- **项目文档确认**：`Wechat2RSS` 当前说明每个公众号每天检查 1–2 次、延迟 0–24 小时，程序只抓
  最新 20 篇；触发风控后从 15 分钟开始倍增，最大 6 小时。这里是其软件行为，不是微信公布的
  通用额度。
- **供应商文档确认**：AIDATA 当前文章列表接口支持 `offset/page_size`、一小时缓存和强制刷新。
  2026-08-24 页面显示普通请求 $0.01、缓存结果 $0.0005；价格会变，部署前必须重新核对。
- **明确推断**：未发现微信为“任意公众号历史文章”提供官方、稳定、可购买的统一额度。可观测的
  风控码和等待时间只能用于保守状态机，不能宣传为官方 SLA 或精确日限额。

## 采用结论

| 路线 | 能力 | 已知限制 | 本项目决策 |
| --- | --- | --- | --- |
| 用户提供文章 URL | 单篇正文 | 不枚举历史；需防 SSRF | 第一优先级 |
| 微信官方素材/发布 API | 自有或授权公众号 | 依赖该账号 access token 与当前接口权限，不覆盖任意公众号历史 | 授权账号优先 |
| `we-mp-rss` 公众号后台采集 | 搜索、列表、正文、RSS | 私有接口会话和风控，无官方稳定额度 | 默认核心，增加持久预算/游标/熔断 |
| AIDATA/同类付费 API | 分页文章列表和缓存 | 计费、字段与供应商依赖，价格可变 | 可选、允许域名且预算封顶的补采/降级 |
| 微信读书 | 低频发现近期群发文章 | 通常最近约 20 篇、可能延迟、账号风控 | 实验性且默认关闭 |

## 核验来源

- 核心与许可证：[`rachelos/we-mp-rss`](https://github.com/rachelos/we-mp-rss)、[MIT](https://github.com/rachelos/we-mp-rss/blob/main/LICENSE)。
- `Wechat2RSS`：[仓库](https://github.com/ttttmr/Wechat2RSS)、[QA/限频与历史范围](https://github.com/ttttmr/Wechat2RSS/blob/master/deploy/qa.md)、[API](https://github.com/ttttmr/Wechat2RSS/blob/master/deploy/api.md)、[部署协议](https://github.com/ttttmr/Wechat2RSS/blob/master/deploy/agreement.md)。
- 官方授权范围：[已发布内容](https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_batchget.html)、[永久素材](https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Get_materials_list.html)。官方页面在本次自动抓取环境中不可解析，部署时需在公众号后台按实际账号权限复核。
- 付费接口：[AIDATA 文章列表](https://aidata.vip/zh-cn/api/endpoints/weixin/mp/article/list)。
- 开源参考：[`cooderl/wewe-rss`](https://github.com/cooderl/wewe-rss)、[`wechat-article-exporter`](https://github.com/wechat-article/wechat-article-exporter/issues/200)、[`wx-kit`](https://github.com/monkeychen/wx-kit/blob/main/AGENTS.md)、[`wechat-mp-article-list`](https://github.com/Alex-giao/wechat-mp-article-list/blob/main/references/backend-workflow.md)。

## 限频原则

- 本次核验未发现面向任意公众号历史采集的官方稳定数值额度，不能把经验值写成官方指标。
- 不通过代理池、验证码绕过、Cookie 隐匿或限频后轮换账户规避限制。
- 默认每账户每提供方一个活动请求；`Retry-After` 优先，否则使用 15、30、60、120、240、360 分钟退避。
- 新订阅只发现一页；历史补采由用户指定范围并持久化游标。
- 只有页面结果成功落库后推进游标；认证失败禁用账户并持久记录错误，通知属于后续可选投递能力。
- 共享同一后台凭据的工作区共用一个总预算和来源任务；落库后再做工作区扇出，不能通过创建用户
  或账户别名重复消耗上游接口。

## 后台存储与消息架构

| Profile | Transaction store | Coordination | Event transport | Content store | Intended use |
| --- | --- | --- | --- | --- | --- |
| Lite | SQLite + WAL | DB polling / in-process | none | local filesystem | 单机试用、迁移和离线使用 |
| Standard | PostgreSQL | Redis | DB outbox + Redis wakeup | local or S3/MinIO | 推荐生产模式 |
| Distributed | PostgreSQL | Redis | MQTT + DB outbox replay | S3/MinIO | 多采集节点和跨网络部署 |

- PostgreSQL 是 Standard/Distributed 的最终事实源，并可使用全文索引、JSONB；语义向量通过可选
  `pgvector` 扩展启用，不成为基础启动条件。
- Redis 只保存可重建缓存、租约、限频令牌和任务通知；权威任务状态仍写数据库。
- MQTT 采用至少一次投递，消息只携带事件 ID 和最小路由信息；消费者按数据库幂等键读取真实载荷。
- 本地文件和 S3/MinIO 共用内容寻址键；当前已提供适配器与指针表，但旧 `articles` 正文的实际
  搬迁仍需单独的数据迁移门禁。

## 许可证与复用

- `we-mp-rss` 是 MIT 核心。
- `Wechat2RSS` 公开仓库不等于其付费程序源码，且部署协议明确限制商业用途、公开服务和二次分发；
  本项目只借鉴公开文档中的行为和限频策略。
- 当前 `wechat-download-api` 是 AGPL-3.0-only；只迁移需求、数据映射和行为，不复制源码。
- `wewe-rss` 可作为 MIT 参考，但项目归档且远程中继不进入运行时依赖。
