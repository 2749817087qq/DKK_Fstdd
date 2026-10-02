# 切片规划 — 2026-09-16-inbox-review-sync

> 模式：standard｜能力：经验回传审核池拉取与发布
> 对应 Spec：`canonical/specs/code/2026-09-16-inbox-review-sync.yaml`
> 测试计划：`test-plan.md`（TC-IRS-001 ~ TC-IRS-016）

## 切片清单

### Slice 1 — 审核池读取与安全解析（review-pool-read）

| 项 | 内容 |
|---|---|
| **实现** | `tools/inbox_pull.py` 读取待审核池，解析投稿元数据，支持分页/批量读取与异常处理 |
| **对应 TC** | TC-IRS-001 ~ TC-IRS-006 |
| **依赖** | 现有 `tools/inbox_server.py` 的投稿目录与元数据格式 |
| **风险** | 池内文件可能损坏、缺字段或包含不可信文本；读取过程必须保持只读 |
| **验证结果** | `upstream/tests/test_inbox_pull.py` 覆盖并通过 |
| **状态** | done |

### Slice 2 — 脱敏与发布到经验库（sanitize-and-publish）

| 项 | 内容 |
|---|---|
| **实现** | 复用 `share_experience.py` 的脱敏规则，发布审核通过的经验，保留来源与审核元数据，避免凭证、邮箱、绝对路径、IPv4 等泄漏 |
| **对应 TC** | TC-IRS-007 ~ TC-IRS-012 |
| **依赖** | Slice 1 的安全解析；现有经验文件格式与发布通道 |
| **风险** | 脱敏误伤合法文件名/域名，或审核失败后重复发布；必须使用幂等标识 |
| **验证结果** | `upstream/tests/test_inbox_pull.py` 覆盖并通过 |
| **状态** | done |

### Slice 3 — 端点协议与批量回传回归（endpoint-contract）

| 项 | 内容 |
|---|---|
| **实现** | 保证投稿端点单条/批量请求、按条数限流、429 Retry-After、拒绝不计数，以及客户端重试契约一致 |
| **对应 TC** | TC-IRS-013 ~ TC-IRS-016 |
| **依赖** | `tools/inbox_server.py` 与客户端批量回传实现 |
| **风险** | 把限流误做成按请求计数，或逐条 POST 导致大批量投稿撞限流 |
| **验证结果** | `upstream/tests/test_inbox_endpoint.py` 覆盖并通过；端点相关 44 项通过 |
| **状态** | done |

## 执行顺序

```text
Slice 1（只读解析） -> Slice 2（脱敏发布）
Slice 3（端点协议回归）可与 Slice 1/2 的测试准备并行，但最终发布验收串行
```

## 证据与边界

- 本 change 只覆盖经验审核池的读取、脱敏、发布和端点协议回归；不承担分布式任务控制面。
- 代码已经存在并已提交；本文件补录真实实现的 Phase 3 结构，不声称重新执行未发生的部署步骤。
- 相关实测：`test_inbox_pull.py` 23 passed，`test_inbox_endpoint.py` 44 passed。
- TC-IRS-001 ~ TC-IRS-016 在 `upstream/tests/test_inbox_pull.py` 中有完整标注，覆盖差集为 0。
- 需要注意：当前 `.fstdd.yaml` 的 `phases.build.slices_completed` 尚未由受控 CLI 写入；Gate 3 / BUILD→DELIVER 仍必须在具备受控证据写入能力后进行，不得手改状态文件。
