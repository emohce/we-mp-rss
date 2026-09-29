# SupSub 服务与连接器核验

Last verified: 2026-08-30（公开价格、CLI 当前文档；受保护接口未执行）

Adoption state: `researched`（未安装、未登录、未购买、未执行受保护接口）

## 已核验事实

| 事实 | 证据等级 | 2026-08-30 公开复核 |
| --- | --- | --- |
| 产品定位 | 官方产品页 | 公众号、网站、X 与 RSS/Atom/JSON 的托管聚合，包含 AI 摘要、关注点筛选和统一阅读 |
| 输出/迁移 | 官方产品页 FAQ | 支持 RSS、Atom、JSON Feed；声明可通过 OPML 导入并保留源与分组 |
| 价格与额度 | 官方公开价格接口 | 基础版月付 ¥29；年付 ¥299，年付原价字段 ¥348；200 个订阅源、10 个关注点 |
| 试用 | 官方产品页 FAQ | 7 天，页面声明与会员功能一致、仅时效不同 |
| CLI | 官方源代码与文档 | `@supsub/cli` 0.4.3，MIT；支持订阅、搜索、关注点、分组、未读和精读，支持 JSON 输出 |
| 登录 | 官方 CLI 认证文档 | OAuth Device Flow 是唯一登录入口，没有 API Key 旁路；凭据保存在本地权限受限文件中 |
| 精读 | 官方 CLI 精读文档 | 按次消耗月度额度；CLI 没有获取原文接口；结果可本地缓存 |
| 分享 | 官方 CLI 精读文档 | 精读分享公开访问，当前没有撤销接口 |
| 出站提醒 | 2026-09-29 官方首页 | 持续抓取；关注点筛选把高相关内容排在阅读器内（页面原文「推到眼前」）。同时输出 RSS、Atom、JSON。首页未列邮件、微信或 webhook 提醒。外部阅读器轮询 Feed 后的提醒不属于本产品能力 |

2026-08-24 价格接口响应曾包含 `Rate-Limit-Total: 120`；本次未复核此响应头，它只能证明该公开价格端点当时的响应策略，
不能推断内容、搜索、Feed 或 CLI 的通用请求额度。页面中的“12,000+ 信息源”“3× 阅读效率”和
“92% 摘要满意度”属于营销陈述，本项目不把它们作为容量或验收依据。

## 官方证据

- 产品与价格：[SupSub 首页/定价](https://supsub.net/#pricing)、[公开价格接口](https://supsub.net/api/plans/standard)。
- CLI：[官方仓库](https://github.com/SupSub-AI/supsub-cli)、[完整文档](https://supsub-ai.github.io/supsub-cli/)、[MIT License](https://github.com/SupSub-AI/supsub-cli/blob/master/LICENSE)。
- 自动化契约：[JSON 输出](https://supsub-ai.github.io/supsub-cli/reference/output)、[认证](https://supsub-ai.github.io/supsub-cli/reference/auth)、[精读](https://supsub-ai.github.io/supsub-cli/reference/deepread)、[核心概念](https://supsub-ai.github.io/supsub-cli/guide/concepts)。
- 历史核验提交：2026-08-24 的 `84744549dfc35e8d829e0c7a4c144b51cf2b8659`；本次只确认当前
  [package.json](https://github.com/SupSub-AI/supsub-cli/blob/master/package.json) 仍为 `0.4.3`，不宣称提交未变。
- 本次命令语义依据：[订阅文档](https://github.com/SupSub-AI/supsub-cli/blob/master/docs/reference/sub.md)、
  [JSON 信封](https://github.com/SupSub-AI/supsub-cli/blob/master/docs/reference/output.md)。

## 与本项目的角色关系

SupSub 不替代 `we-mp-rss`，也不成为本地文章、反馈或任务的最终事实源。它适合承担四种可选角色：

1. **Feed 入站/出站**：把用户授权的 RSS、Atom 或 JSON Feed 作为低耦合内容通道；也可让 SupSub
   订阅本项目发布的 Feed；
2. **订阅迁移**：通过 OPML 做人工触发、可预览的一次性导入/导出，首版不做持续双向同步；
3. **只读发现**：使用 CLI 的全站搜索、订阅列表、内容列表和关注点结果，作为第二
   发现源并保留 SupSub 外部身份；
4. **可选增强**：经额度确认后请求精读，把结果保存为供应商派生版本，不覆盖本地正文、摘要或
   用户反馈。

SupSub 自身已经聚合公众号，并不意味着可以用它绕过微信或其他平台限制。本项目按独立供应商预算
管理，禁止在 `we-mp-rss` 限频后自动切换账户或并行重复抓取同一来源。

## 分阶段接入顺序

| Phase | 能力 | 自动化范围 | 当前状态 |
| --- | --- | --- | --- |
| S0 | Feed/OPML 格式、认证与稳定 ID | 本地格式样例 | 通用格式通过；实际供应商样例/认证仍缺失 |
| S1 | CLI `sub list/contents`、`search`、`focus list/contents` | 登录后只读；版本固定；JSON 严格解析 | 参数计划/信封测试通过；未执行 CLI、未证明真实字段映射 |
| S2 | 单向 OPML/订阅同步 | 先预览；逐批外部写入；幂等和回环抑制 | 未授权 |
| S3 | 精读增强 | 每篇先查额度；明确确认；结果缓存 | 未授权 |
| S4 | 已读/分组/分享同步 | 不进入定时任务 | 默认禁止 |

不采用“已读双向同步”作为近期目标：SupSub CLI 只支持整源或整关注点不可逆标记，且没有单篇已读；
分组成员编辑存在整体覆盖和并发冲突风险。精读分享当前公开且不可撤销，也不能由自动化生成。

## 连接器运行契约

- CLI 必须使用绝对可执行文件、固定允许命令、参数数组和 `-o json`，禁止通过 shell 拼接用户输入。
- 首次 OAuth 登录由用户本人在浏览器完成；不安装 CLI、不写 PATH、不写凭据，除非另行授权。
- 凭据只通过专用文件或 secret manager 引用；不得写入数据库明文、日志、MQTT 或诊断 API。
- 自动化环境固定 CLI 版本并关闭后台自更新；升级需重新跑契约测试和能力快照。
- JSON 结果受响应大小、超时和结构校验约束；stdout 仅解析数据，stderr 只作为脱敏诊断。
- 官方 `sub contents` 默认只返回未读；本地只读参数计划固定 `--all`，保持“最近文章”和已读状态无关。
  `sourceId` 是整型，不等于公众号外部 ID；首版只接受 MP/WEBSITE。`mp.search` 创建异步任务，
  不作为只读发现调用；markread、deepread、分享及写入命令不在允许名单中。
- `provider + external_type + external_id` 形成外部身份；本地文章另以规范 URL/内容证据去重。
- 所有供应商摘要、关注点分数和精读结果都保留来源、模型/版本、生成时间和用量收据。

## 正式 canary 前仍需核验

- RSS/Atom/JSON Feed 的实际 URL、认证方式、增量/缓存头、分页与 token 撤销；
- OPML 导入/导出的公开格式、分组冲突和删除语义；
- 搜索与内容接口的正式额度、SLA、数据保留和稳定错误码；
- 精读套餐的月度额度与额外计费规则；
- 服务条款、隐私政策、内容授权、数据删除/导出和自动化使用边界；
- 测试账号下的字段样例、重复内容、发布时间时区及外部 ID 稳定性。

这些缺口未关闭前，供应商继续保持 `researched`。本地格式、参数计划、输出信封和用量门禁的离线
代码证据单独登记，不能提升供应商状态。真实 Feed、鉴权、分页、错误/额度和内容字段仍需独立 canary。

## 2026-09-29 提醒渠道

复核范围只有公开首页 [supsub.net](https://supsub.net/)。未重跑价格接口，未核对 CLI 版本，未登录。
采用状态保持 `researched`。

首页的「推到眼前」是站内关注点排序。公开页没有邮件、微信或 webhook 提醒。RSS、Atom、JSON 仍是
出站内容通道；若阅读器自己发提醒，该提醒不属于 SupSub。路线对照见
[采集路线](wechat-collection-landscape.md)。
