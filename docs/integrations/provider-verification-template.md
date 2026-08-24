# 外部连接器核验模板

每个新增供应商复制本模板形成独立研究文件。只记录摘要化事实和采用决定，不保存登录凭据、原始
响应、逐字对话、命令输出或隐藏推理。

## 1. Snapshot

```yaml
provider: example
verified_at: YYYY-MM-DD
evidence_version: commit-or-page-version
state: researched
next_review_at: YYYY-MM-DD
owner: app-root
```

## 2. Primary evidence

- 官方产品页、定价接口、API/CLI 文档、许可证、服务条款和隐私政策；
- 每条事实标记为 `official-page`、`official-api`、`official-source`、`runtime-canary` 或 `inference`；
- 动态价格、额度和 SLA 必须带日期，不得从单个响应头推断全站额度。

## 3. Capability matrix

逐项核验 `discover`、`ingest`、`subscription_sync`、`search`、`enrich`、`deliver` 和
`state_sync`，并记录输入、输出、分页、增量游标、最大响应、幂等、错误码和重试建议。

## 4. Identity and provenance

- 外部来源 ID、内容 ID、规范 URL、发布时间与更新时间；
- 本地规范来源/文章的映射规则和碰撞处理；
- 原文、供应商摘要、供应商 AI 结果和本地 AI 结果必须分字段保存。

## 5. Authentication and secrets

- OAuth、API Key、Cookie、Feed token 或设备授权；
- 凭据保存位置、文件权限、续期/撤销方式和多工作区共享边界；
- 是否支持无头运行；任何用户交互步骤必须保持用户本人完成。

## 6. Limits and cost

- 套餐价格、订阅数、关注点、请求/并发、按次额度、缓存、保留期和退款/撤销能力；
- 记录用量查询方式和账本字段；不能查询余额的计费动作默认禁止自动化。

## 7. Mutations and risk

列出所有外部写操作并标注 R2/R3/R4：是否可逆、是否公开、是否收费、是否支持幂等、是否需要
预览与逐项确认。整批删除、整源已读、不可撤销分享不得放进无人值守计划任务。

## 8. Security, privacy and contract

- SSRF、重定向、响应上限、内容类型、HTML 主动内容和供应链风险；
- 数据处理地域、训练/二次使用、删除/导出、账号共享和商业用途边界；
- 未能读取或确认的合同条款必须标记为 `unverified`，不能用推断补齐。

## 9. Adoption decision

写明连接器角色、首选方向、回退路径、是否替代核心、未满足门禁和下一次复核时间。推荐默认采用
单工作区、单来源、单页、只读、低频 canary。

## 10. Acceptance evidence

分开记录：静态/离线契约、测试账号 canary、真实数据库、浏览器、部署和生产。任一层通过都不能
替代下一层验收。
