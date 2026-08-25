# 微信公众号智能聚合系统原始需求摘要

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-25
Spec: [spec.md](spec.md)
Source format: `chat-requirement-summary`
Capture fidelity: `normalized-material-requirement`

## RAW-001

```yaml
raw_id: RAW-001
captured_at: 2026-08-24
state: active
source_lineage: current-user-request-and-approved-plan
privacy_boundary: no-verbatim-prompt-or-transcript
```

用户要求以 `rachelos/we-mp-rss` 为唯一产品核心，参考 `ttttmr/Wechat2RSS`，并整合现有
`wechat-download-api` 的可用行为。系统需要使用 SQLite3，支持每日采集与日期汇总、单篇和
批量下载、AI 主题过滤、基于反馈的个人偏好、浮窗式管理、多用户隔离、RSS/MCP/投递以及
可恢复的限频控制。现有仓库提交要安全回滚并拆分到 `czz-main`，所有提交保持本地。

## RAW-002

```yaml
raw_id: RAW-002
captured_at: 2026-08-24
state: active
source_lineage: current-user-architecture-correction
privacy_boundary: no-verbatim-prompt-or-transcript
```

用户明确取消 SQLite3 作为唯一核心存储的限制，要求重新梳理底层后台架构，并允许采用更高阶
数据库、Redis 和 MQTT。系统仍以原始内容聚合、AI 过滤、反馈学习、汇总和下载目标为准，
技术选型应从可靠性、扩展性与本地部署能力出发。

## RAW-003

```yaml
raw_id: RAW-003
captured_at: 2026-08-24
state: active
source_lineage: current-user-integration-expansion
privacy_boundary: no-verbatim-prompt-or-transcript
```

用户要求结合 SupSub 当前提供的托管订阅、AI 筛选、RSS/Atom/JSON、OPML 和 CLI 能力扩充原始
需求，并把本次核验沉淀为可继续接入更多服务的通用方式。外部服务不能取代 `we-mp-rss` 核心；
未来集成需要可验证、可分阶段启用，并明确认证、费用、限额、同步冲突、不可逆操作和隐私边界。

## RAW-004

```yaml
raw_id: RAW-004
captured_at: 2026-08-25
state: active
source_lineage: current-user-document-migration-sync
privacy_boundary: no-verbatim-prompt-or-transcript
```

用户要求确认所有相关文档均已更新到新的核心项目目录，并把此前的原始需求、实现调研和旧项目中
可复用的行为完整迁移同步。同步结果需要可追溯，明确区分已实现、部分实现、待实现、仅供参考和
已被后续需求否决的内容；不能把旧仓库文档存在的功能直接宣称为当前核心已经交付。

## Capture Boundary

- Included: 产品范围、仓库角色、技术约束及其后续覆盖、交互方式、采集与限频、外部连接器、
  原始需求/实现调研迁移、状态分类、验证和 Git 边界。
- Excluded: 对话逐字稿、工具输出、凭据、Cookie、隐藏推理。
- Audio unavailable or unclear terms: `AR` 已按上下文确认为 AI 内容过滤。
