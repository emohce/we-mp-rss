# 微信公众号智能聚合系统文档索引

Last synchronized: 2026-08-25

本目录是 `we-mp-rss` 智能聚合项目的唯一当前文档入口。旧 `wechat-download-api` 与
`Wechat2RSS` 只保留证据和行为参考角色；后续需求、采用决策、验证结论与实现状态都在本仓库更新。

## 权威顺序

| 顺序 | 文档 | 作用 |
| --- | --- | --- |
| 1 | [原始需求摘要](tasks/260824-wechat-intelligence-hub/raw-requirement.md) | 保留每次用户补充和覆盖关系，不保存逐字对话。 |
| 2 | [Controlled Spec](tasks/260824-wechat-intelligence-hub/spec.md) | 当前产品需求与边界的唯一规范化权威。 |
| 3 | [Intelligence Hub v2](intelligence-hub.md) | 已交付架构、配置、交互和运行门禁。 |
| 4 | [旧项目迁移矩阵](migrations/wechat-download-api.md) | 把旧能力逐项标成已实现、部分实现、计划、仅参考或已否决。 |
| 5 | [采集路线与开源边界](research/wechat-collection-landscape.md) | 采集原理、限频、替代 API、开源和许可证调研。 |
| 6 | [SupSub 核验](research/supsub-integration.md) | SupSub 当前能力、价格快照、风险和分阶段采用决定。 |
| 7 | [连接器注册表](integrations/README.md) | 后续托管服务、Feed、付费 API、AI 和投递平台的统一接入契约。 |
| 8 | [计划](tasks/260824-wechat-intelligence-hub/plan.md) · [任务台账](tasks/260824-wechat-intelligence-hub/tasks.md) · [验证](tasks/260824-wechat-intelligence-hub/verify.md) · [交接](tasks/260824-wechat-intelligence-hub/handoff.md) · [变更清单](tasks/260824-wechat-intelligence-hub/changes.md) | 执行与验收证据，不替代 Spec。 |

## 仓库角色

| 仓库 | 角色 | 允许进入当前核心的内容 |
| --- | --- | --- |
| `rachelos/we-mp-rss` | 唯一产品核心 | 需求、实现、测试、运行文档和后续迭代。 |
| `ttttmr/Wechat2RSS` | 公开行为与限频参考 | 经核验的行为、限制和设计启发；不复制受限代码或付费程序。 |
| `emohce/wechat-download-api` | 旧需求与实现研究来源 | 产品行为、数据映射、迁移不变量和风险证据；不复制 AGPL 源码。 |

## 状态词

- `implemented-current`：当前核心源码存在，且至少有相应静态或聚焦验证；不等于真实环境已验收。
- `partial-current`：核心已有相近实现，但旧需求的格式、范围、租户或安全不变量仍有缺口。
- `planned`：已进入 Spec，但尚无当前核心实现。
- `researched`：已有公开证据和采用判断，尚未进入运行时。
- `reference-only`：只保留证据，不成为当前产品契约。
- `superseded`：被后续明确需求或安全边界替代，不应重新实现。

## 同步边界

本次迁移同步的是原始需求、可复用行为、实现调研、数据映射、许可证结论和未完成门禁。以下内容
不会复制进核心仓库：旧项目源码、Cookie/token、SQLite 数据、运行日志、旧仓库专属 AI 规则、历史
任务过程噪声，以及把代理池或 TLS 指纹描述为规避平台限制的方案。

“文档已同步”只说明相关决定可从本索引追溯；具体能力是否已经交付，以迁移矩阵和验证记录中的状态
为准。
