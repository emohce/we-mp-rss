# Changes：微信公众号智能聚合系统

Updated: 2026-08-25

## 1. 概览

| 批次 | 提交 | 文件数 | 核心说明 |
| --- | --- | --- | --- |
| Governance baseline | `a1efa5b` | 8 | 建立受控需求、计划、研究与回滚基线。 |
| Durable foundation | `7bbe683` | 14 | 增加分档存储、租户模型、租约任务、outbox 和内容存储适配层。 |
| Intelligence backend | `426c9c1` | 30 | 增加采集、限频、AI/反馈/日报/导出、v2 API 和离线迁移契约。 |
| Floating workspace | `754b846` | 237 | 增加全局右侧浮窗、API 绑定和经验证的生产构建产物。 |
| Documentation closeout | `13057d4` | 12 | 同步 README、运维架构、研究、验证、错误记忆和交接边界。 |
| Provider integration revision | `fd666a7` | 12 | 增加通用连接器注册表、SupSub 核验和 RAW-003。 |
| Legacy documentation migration | current docs batch | 13 | 增加总索引、旧项目迁移矩阵和 RAW-004，并同步所有当前权威。 |

## 2. 交付物清单

| 对象 | 类型 | 核心说明 |
| --- | --- | --- |
| `docs/tasks/260824-wechat-intelligence-hub/` | 新增 | Controlled 任务的唯一过程台账。 |
| `docs/research/wechat-collection-landscape.md` | 新增 | 采集路线、限制、许可证和采用决策。 |
| `docs/intelligence-hub.md` | 新增 | 架构档位、租户/采集边界、API、配置和迁移手册。 |
| `core/intelligence/` | 新增/修改 | 可移植模型、持久任务/outbox、采集器、分析、反馈、日报和测试。 |
| `apis/intelligence.py` / `jobs/intelligence.py` | 新增 | 认证 v2 API、公开摘要页和可控后台 Worker。 |
| `web_ui/src/components/intelligence/IntelligenceHub.vue` | 新增 | 不增加路由的统一智能浮窗。 |
| `compose/` / `tools/intelligence_schema.py` | 新增 | Distributed 示例和只读/离线数据库交接工具。 |
| `docs/integrations/` | 新增 | 通用连接器能力、风险、生命周期、事实源和供应商核验模板。 |
| `docs/research/supsub-integration.md` | 新增 | SupSub 当前价格/能力/CLI 边界、采用顺序和未关闭门禁。 |
| `docs/README.md` | 新增 | 核心仓库的需求、架构、研究、迁移、连接器和过程文档唯一入口。 |
| `docs/migrations/wechat-download-api.md` | 新增 | 逐项标记旧行为的当前实现状态、数据映射、安全不变量和许可证边界。 |
| `docs/tasks/260824-wechat-intelligence-hub/` | 更新 | 增加 RAW-004、Spec revision 4、WU-8 及对应验证/交接证据。 |
| `docs/intelligence-hub.md` / `docs/research/wechat-collection-landscape.md` | 更新 | 收敛旧行为状态并纠正 MCP/批量导出的实现表述。 |
| `ReadMe.md` / `README.zh-CN.md` | 更新 | 暴露需求、调研和迁移文档总入口。 |

## 3. 逐批清单

- `a1efa5b`：8 个文档/规则文件，487 行新增。
- `7bbe683`：14 个文件，1,455 行新增、41 行删除。
- `426c9c1`：30 个文件，5,448 行新增、44 行删除。
- `754b846`：237 个文件，2,349 行新增、1,776 行删除；主要为构建哈希资源换代。
- `13057d4`：12 个文件，341 行新增、54 行删除。
- `fd666a7`：12 个文档文件，增加通用连接器与 SupSub 需求/研究同步。
- current docs batch：13 个文档文件，315 行新增、30 行删除。

## 4. 明确没做的

| 对象 | 数量 | 核心说明 |
| --- | --- | --- |
| 真实微信/付费 API/AI CLI 调用 | 0 | 受凭据、计费和运行时门禁约束。 |
| 用户数据库迁移 | 0 | 只提供只读检查器和离线 DDL。 |
| Redis/MQTT 实际连接 | 0 | 只验证适配契约与 Compose 配置。 |
| 部署、推送和浏览器验收 | 0 | 均保留为独立门禁。 |
| SupSub 安装、登录、购买、同步、精读和分享 | 0 | 本轮仅扩充需求与公开证据。 |
| 旧 AGPL 源码、凭据、SQLite 数据和仓库专属治理文档复制 | 0 | 只迁移需求、行为研究、数据映射和采用决定。 |
| MCP、租户化 Feed、批量导出日期/增量/HTML/EPUB 补齐 | 0 | 已进入计划/部分实现清单，未伪装为本轮代码交付。 |

## 5. 用户可见行为变化

- 登录后全局显示 `AI 聚合` 浮动入口，而非继续扩张管理路由。
- 支持收件箱主题/相关度/状态过滤、单篇多格式下载、逐篇反馈、偏好建议和日期日报分享。
- 新后台任务默认关闭；未迁移数据库时不会自动采集或写入外部系统。

## 6. 顺手发现但未处理

- 上游 `tools/fix_db.py` 存在未终止字符串，导致仓库级 `compileall` 失败；本任务未改该文件。
- 前端依赖保留 10 个既有审计项，并有大包、直接 `eval` 和动态导入警告。
- 付费接口价格、微信权限和风控额度都不是稳定静态事实，正式启用前必须再次联网核验。
- SupSub 尚缺测试账号下的 Feed/OPML/API 字段、合同、配额与冲突证据，不能宣传为已集成。
- 当前核心未发现 MCP 入口；现有批量导出未覆盖旧项目的全部范围/格式/本地只读契约，迁移矩阵已
  将两者分别标为 `planned` 和 `partial-current`。

## 7. 回归数字

- 后端：39/39 通过。
- 数据库：3 个方言 DDL 均成功生成，每份 460 行。
- 前端：Vite 生产构建通过；14/14 首页资源引用存在，构建资源树一致。
- 分布式配置：Compose 解析通过；真实基础设施未连接。
