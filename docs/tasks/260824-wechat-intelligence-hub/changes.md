# Changes：微信公众号智能聚合系统

## 1. 概览

| 批次 | 提交 | 文件数 | 核心说明 |
| --- | --- | --- | --- |
| Governance baseline | `a1efa5b` | 8 | 建立受控需求、计划、研究与回滚基线。 |
| Durable foundation | `7bbe683` | 14 | 增加分档存储、租户模型、租约任务、outbox 和内容存储适配层。 |
| Intelligence backend | `426c9c1` | 30 | 增加采集、限频、AI/反馈/日报/导出、v2 API 和离线迁移契约。 |
| Floating workspace | `754b846` | 237 | 增加全局右侧浮窗、API 绑定和经验证的生产构建产物。 |
| Documentation closeout | 本提交 | 本批次 | 同步 README、运维架构、研究、验证、错误记忆和交接边界。 |

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

## 3. 逐批清单

- `a1efa5b`：8 个文档/规则文件，487 行新增。
- `7bbe683`：14 个文件，1,455 行新增、41 行删除。
- `426c9c1`：30 个文件，5,448 行新增、44 行删除。
- `754b846`：237 个文件，2,349 行新增、1,776 行删除；主要为构建哈希资源换代。

## 4. 明确没做的

| 对象 | 数量 | 核心说明 |
| --- | --- | --- |
| 真实微信/付费 API/AI CLI 调用 | 0 | 受凭据、计费和运行时门禁约束。 |
| 用户数据库迁移 | 0 | 只提供只读检查器和离线 DDL。 |
| Redis/MQTT 实际连接 | 0 | 只验证适配契约与 Compose 配置。 |
| 部署、推送和浏览器验收 | 0 | 均保留为独立门禁。 |

## 5. 用户可见行为变化

- 登录后全局显示 `AI 聚合` 浮动入口，而非继续扩张管理路由。
- 支持收件箱主题/相关度/状态过滤、单篇多格式下载、逐篇反馈、偏好建议和日期日报分享。
- 新后台任务默认关闭；未迁移数据库时不会自动采集或写入外部系统。

## 6. 顺手发现但未处理

- 上游 `tools/fix_db.py` 存在未终止字符串，导致仓库级 `compileall` 失败；本任务未改该文件。
- 前端依赖保留 10 个既有审计项，并有大包、直接 `eval` 和动态导入警告。
- 付费接口价格、微信权限和风控额度都不是稳定静态事实，正式启用前必须再次联网核验。

## 7. 回归数字

- 后端：39/39 通过。
- 数据库：3 个方言 DDL 均成功生成，每份 460 行。
- 前端：Vite 生产构建通过；14/14 首页资源引用存在，构建资源树一致。
- 分布式配置：Compose 解析通过；真实基础设施未连接。
