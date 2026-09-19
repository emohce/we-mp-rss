# Worktree Tasks

Markers and timestamps are quick-resume hints. Integration still requires live Git ancestry and lifecycle-gate checks.

<!-- worktree-control-observations:start -->
| 任务与主目录记录 | 进度 / 保留 | 核心规划 | 下一步 / 恢复条件 | 标记 |
| --- | --- | --- | --- | --- |
| [260830-worktree-integration](docs/worktree-control/260830-worktree-integration.md) | head merged into czz-main; ~272 uncommitted changes pending review / active | worktree-integration line for wechat-intelligence-hub; residual prototype/requirements-hub draft work | review uncommitted diff, then adopt into lifecycle or remove checkout keeping the branch；owner resolves uncommitted-diff disposition | `427c675af0dae476` |
| [260908-observatory-rule-delivery](docs/worktree-control/260908-observatory-rule-delivery.md) | 5 commits ahead of czz-main (87442c0..9cda119); dirty generated-rules cleanup overlaps 73dee44 / active | observatory/rule-delivery line restoring naming/reply/fidelity rules and syncing compacted rules | diff commits and dirty state vs czz-main, then integrate via main gate or discard；owner completes overlap review | `f00c7ce6d46f4b95` |
| [media-subscription-redesign-eba67f](docs/worktree-control/media-subscription-redesign-eba67f.md) | 22 commits ahead of czz-main incl. spec-revision-9 merge 1229921; dirty generated-rules cleanup / active | media-subscription redesign line; preference-ledger RAW-014 and rebuilt frontend assets | review commit range and dirty diff vs czz-main, then main-gate integration or discard；owner completes review | `5928ecded5990966` |

[Git、规划摘要与缓存引用记录](docs/worktree-control/index.json#L1)
<!-- worktree-control-observations:end -->
