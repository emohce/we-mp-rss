# 微信公众号采集路线与开源边界

Last verified: 2026-08-24

## 采用结论

| 路线 | 能力 | 已知限制 | 本项目决策 |
| --- | --- | --- | --- |
| 用户提供文章 URL | 单篇正文 | 不枚举历史；需防 SSRF | 第一优先级 |
| 微信官方素材/发布 API | 自有或授权公众号 | 不覆盖任意公众号历史 | 授权账号优先 |
| `we-mp-rss` 公众号后台采集 | 搜索、列表、正文、RSS | 私有接口会话和风控，无官方稳定额度 | 默认核心，增加持久预算/游标/熔断 |
| AIDATA | 分页文章列表和缓存 | 计费、供应商依赖 | 可选、预算封顶的补采/降级 |
| 微信读书 | 低频发现近期群发文章 | 通常最近约 20 篇、可能延迟、账号风控 | 实验性且默认关闭 |

## 核验来源

- 核心与许可证：[`rachelos/we-mp-rss`](https://github.com/rachelos/we-mp-rss)、[MIT](https://github.com/rachelos/we-mp-rss/blob/main/LICENSE)。
- `Wechat2RSS`：[仓库](https://github.com/ttttmr/Wechat2RSS)、[QA/限频与历史范围](https://github.com/ttttmr/Wechat2RSS/blob/master/deploy/qa.md)、[API](https://github.com/ttttmr/Wechat2RSS/blob/master/deploy/api.md)、[部署协议](https://github.com/ttttmr/Wechat2RSS/blob/master/deploy/agreement.md)。
- 官方授权范围：[已发布内容](https://developers.weixin.qq.com/doc/service/api/public/api_freepublish_batchget)、[永久素材](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_batchgetmaterial)。
- 付费接口：[AIDATA 文章列表](https://aidata.vip/zh-cn/api/endpoints/weixin/mp/article/list)。
- 开源参考：[`cooderl/wewe-rss`](https://github.com/cooderl/wewe-rss)、[`wechat-article-exporter`](https://github.com/wechat-article/wechat-article-exporter/issues/200)、[`wx-kit`](https://github.com/monkeychen/wx-kit/blob/main/AGENTS.md)、[`wechat-mp-article-list`](https://github.com/Alex-giao/wechat-mp-article-list/blob/main/references/backend-workflow.md)。

## 限频原则

- 本次核验未发现面向任意公众号历史采集的官方稳定数值额度，不能把经验值写成官方指标。
- 不通过代理池、验证码绕过、Cookie 隐匿或限频后轮换账户规避限制。
- 默认每账户每提供方一个活动请求；`Retry-After` 优先，否则使用 15、30、60、120、240、360 分钟退避。
- 新订阅只发现一页；历史补采由用户指定范围并持久化游标。
- 只有页面结果成功落库后推进游标；认证失败禁用账户并产生一次通知。

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
- 本地文件和 S3/MinIO 共用内容寻址键，避免数据库重复保存大段正文与多份导出缓存。

## 许可证与复用

- `we-mp-rss` 是 MIT 核心。
- `Wechat2RSS` 公开仓库不包含付费后端源码，且部署协议另有限制；只借鉴公开行为。
- 当前 `wechat-download-api` 是 AGPL-3.0-only；只迁移需求、数据映射和行为，不复制源码。
- `wewe-rss` 可作为 MIT 参考，但项目归档且远程中继不进入运行时依赖。
