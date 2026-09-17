# 切片规划 — 2026-09-17-distributed-task-coordination

> 模式：standard｜Capability：分布式任务协调基础能力
> 对应 Spec：`canonical/specs/code/2026-09-17-distributed-task-coordination.yaml`（8 REQ / 16 SC）
> 测试计划：`test-plan.md`（TC-DTC-001 ~ TC-DTC-016）

## 切片清单

### Slice A — FSTDD 审计追认与 Slice 证据写入（gate-and-slice-evidence）

| 项 | 内容 |
|---|---|
| **实现** | 新增 `fstdd gate amend-audit`，以追加方式记录用户追认，保留原始 Gate 审计；新增 `fstdd phase record-slice`，通过受控 CLI 写入 BUILD per-slice 证据并拒绝冲突覆盖 |
| **对应 TC** | Gate：TC-DTC-005、TC-DTC-006；Slice 证据：支撑 TC-DTC-001/002 的 FSTDD 交付前置条件 |
| **依赖** | 主 change Gate 2 已确认；现有 Gate/phase CLI |
| **风险** | 审计修正不能覆盖历史记录；Slice 证据不能允许静默覆盖或手改 YAML |
| **验证结果** | `test_gate.py` + `test_phase.py`：**40 passed** |
| **状态** | done |

### Slice B — 8788 控制面最小闭环（hub-core）

| 项 | 内容 |
|---|---|
| **实现** | 节点注册、任务创建/查询/原子领取、租约/心跳、完成/失败回传、SQLite 存储和幂等键 |
| **对应 TC** | TC-DTC-001 ~ TC-DTC-006、TC-DTC-011 ~ TC-DTC-015 |
| **依赖** | Slice A；D哥 Gate 3 前必须完成并测试 |
| **风险** | 并发领取、租约过期、旧 token 回传、重复请求和数据库恢复 |
| **验证结果** | `upstream/tests/test_fstdd_hub.py`：**8 passed**；覆盖注册、任务幂等、原子领取、租约/旧 token、失败/阻塞消息与 ack |
| **状态** | done |

### Slice C — Git 分支、外部 worktree 与串行集成（git-integration）

| 项 | 内容 |
|---|---|
| **实现** | `tools/fstdd_git.py` 提供每任务 `task/<task_id>` 分支、仓库外 worktree、固定基线 SHA、scope 冲突检查、干净 master 上的 ff-only 串行集成；冲突/脏目标直接失败，不强推、不自动 reset |
| **对应 TC** | TC-DTC-007、TC-DTC-008、TC-DTC-016 |
| **依赖** | Slice B；服务器裸库可用 |
| **风险** | 分支漂移、scope 重叠、master 并发写入和 GitHub 镜像失败 |
| **验证结果** | `upstream/tests/test_fstdd_git.py`：**6 passed**；覆盖外部 worktree、重复请求、分支基线冲突、scope 冲突、ff-only 集成和脏目标拒绝 |
| **状态** | done |

### Slice D — 8788 部署与恢复运维（hub-ops）

| 项 | 内容 |
|---|---|
| **实现** | 独立 systemd unit、127.0.0.1 监听、健康检查、SQLite 冷备、容量告警、与 8787 隔离 |
| **对应 TC** | TC-DTC-009、TC-DTC-010 |
| **依赖** | Slice B、Slice C |
| **风险** | 8787/8788/裸库共享服务器磁盘，远端 SSH 命令可能重复执行 |
| **验证结果** | 待实现 |
| **状态** | pending |

## 执行顺序

```text
Slice A（审计与 FSTDD 证据基础） -> Slice B（控制面闭环）
Slice C（Git 集成） -> Slice D（部署运维）
```

- Slice A、Slice B、Slice C 已完成并通过测试。
- Slice D 尚未实现，不得在 Gate 3 报告中声称已交付。
- 所有后续代码必须继续在本 active Change 的 BUILD 阶段完成。
